from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from orders.models import Order, OrderItem, OrderStatus
from products.models import Category, Product


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer')
        self.other = get_user_model().objects.create_user(username='other')
        self.admin = get_user_model().objects.create_superuser(username='admin', password='test')
        category = Category.objects.create(name='Equipment')
        self.product = Product.objects.create(name='Machine', description='Equipment',
                                             category=category, price='10.25', stock=5)
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.pk): 2}
        session.save()
        self.data = {'shipping_address': 'Москва, дом 1', 'payment_method': 'cash'}

    def create_order(self):
        return Order.create_from_cart(self.user, {str(self.product.pk): 2}, 'Москва', 'cash')

    def test_success_checkout(self):
        response = self.client.post('/checkout/', self.data, follow=True)
        order = Order.objects.get()
        self.assertContains(response, 'успешно оформлен')
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.total_price, Decimal('20.50'))
        self.assertEqual(order.payment_method, 'cash')
        self.assertEqual(order.items.get().price, Decimal('10.25'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.client.session['cart'], {})
        self.product.price = 99
        self.product.save()
        self.assertEqual(order.items.get().price, Decimal('10.25'))

    def test_empty_invalid_and_insufficient_cart(self):
        for cart in [{}, {str(self.product.pk): 6}, {'999999': 1},
                     {str(self.product.pk): 0}, {str(self.product.pk): '1'}]:
            with self.subTest(cart=cart):
                with self.assertRaises(ValidationError):
                    Order.create_from_cart(self.user, cart, 'Москва', 'cash')
                self.assertFalse(Order.objects.exists())
                self.product.refresh_from_db()
                self.assertEqual(self.product.stock, 5)

    def test_all_items_rollback(self):
        product = Product.objects.create(name='Other', category=self.product.category,
                                         price=1, stock=0)
        with self.assertRaises(ValidationError):
            Order.create_from_cart(self.user, {str(self.product.pk): 2, str(product.pk): 1}, 'Москва', 'cash')
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_inactive_product_and_form_validation(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.post('/checkout/', self.data)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(self.client.session['cart'], {str(self.product.pk): 2})
        for data in [{}, {**self.data, 'payment_method': 'invalid'}]:
            response = self.client.post('/checkout/', data)
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(Order.objects.exists())

    def test_permissions_and_csrf(self):
        self.assertRedirects(Client().get('/checkout/'), '/account/login/?next=/checkout/')
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/checkout/', self.data).status_code, 403)
        order = self.create_order()
        url = reverse('orders:cancel', args=[order.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_cancel_restores_stock_once(self):
        order = self.create_order()
        url = reverse('orders:cancel', args=[order.pk])
        self.client.post(url)
        self.client.post(url)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.product.stock, 5)

    def test_transition_rules(self):
        for initial in OrderStatus.values:
            for target in OrderStatus.values:
                order = Order.objects.create(owner=self.user, status=initial)
                allowed = (initial, target) in [('pending', 'paid'), ('pending', 'cancelled'),
                    ('paid', 'shipped'), ('paid', 'cancelled'), ('shipped', 'delivered')]
                if allowed:
                    order.change_status(target, self.admin)
                    self.assertEqual(order.status, target)
                else:
                    with self.assertRaises(ValidationError):
                        order.change_status(target, self.admin)

    def test_user_cannot_pay_or_cancel_paid_order(self):
        order = self.create_order()
        with self.assertRaises(ValidationError):
            order.change_status(OrderStatus.PAID, self.user)
        order.change_status(OrderStatus.PAID, self.admin)
        with self.assertRaises(ValidationError):
            order.change_status(OrderStatus.CANCELLED, self.user)
        order.change_status(OrderStatus.CANCELLED, self.admin)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_database_constraints(self):
        order = self.create_order()
        for values in [{'quantity': 0}, {'price': -1}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                order.items.update(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(order=order, product=self.product, quantity=1, price=1)
        for model, values in [(Order, {'total_price': -1}), (Product, {'price': -1}), (Product, {'stock': -1})]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.all().update(**values)
        from django.db.models.deletion import ProtectedError
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_admin_blocks_delete_and_invalid_status(self):
        order = self.create_order()
        self.client.force_login(self.admin)
        url = reverse('admin:orders_order_change', args=[order.pk])
        response = self.client.post(url, {'status': 'delivered',
            'items-TOTAL_FORMS': 1, 'items-INITIAL_FORMS': 1, 'items-0-id': order.items.get().pk})
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(self.client.post(reverse('admin:orders_order_delete', args=[order.pk])).status_code, 403)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        response = self.client.post(url, {'status': 'cancelled',
            'items-TOTAL_FORMS': 1, 'items-INITIAL_FORMS': 1, 'items-0-id': order.items.get().pk})
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.product.stock, 5)

    def test_late_error_rolls_back_order_and_stock(self):
        from unittest.mock import patch
        with patch('orders.models.OrderItem.objects.create', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                self.create_order()
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)


class ConcurrentCheckoutTests(TransactionTestCase):
    def test_only_one_buyer_gets_last_item(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Требуется PostgreSQL')
        user = get_user_model().objects.create_user(username='concurrent')
        category = Category.objects.create(name='Equipment')
        product = Product.objects.create(name='Last', category=category, price=10, stock=1)
        barrier = Barrier(2)

        def buy():
            close_old_connections()
            try:
                buyer = get_user_model().objects.get(pk=user.pk)
                barrier.wait(timeout=10)
                try:
                    Order.create_from_cart(buyer, {str(product.pk): 1}, 'Москва', 'card')
                    return True
                except ValidationError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: buy(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)
