from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from products.models import Category, Product


class CartTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Hops')
        self.product = Product.objects.create(name='Citra', description='Hops',
                                             price='0.10', stock=5, category=category)
        self.add_url = reverse('shop:cart_add', args=[self.product.pk])
        self.update_url = reverse('shop:cart_update', args=[self.product.pk])
        self.remove_url = reverse('shop:cart_remove', args=[self.product.pk])
        self.cart_url = reverse('shop:cart')

    def test_add_accumulates_quantity_and_shows_message(self):
        self.client.post(self.add_url, {'quantity': 1})
        response = self.client.post(self.add_url, {'quantity': 2}, follow=True)
        self.assertEqual(self.client.session['cart'], {str(self.product.pk): 3})
        self.assertContains(response, 'Товар добавлен в корзину.')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_update_remove_and_empty_cart(self):
        self.client.post(self.add_url, {'quantity': 2})
        self.client.post(self.update_url, {'quantity': 4})
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 4)
        self.client.post(self.remove_url)
        response = self.client.get(self.cart_url)
        self.assertEqual(self.client.session['cart'], {})
        self.assertContains(response, 'Корзина пуста.')
        self.assertEqual(response.context['total'], Decimal('0.00'))

    def test_invalid_quantity_and_stock_do_not_change_cart(self):
        self.client.post(self.add_url, {'quantity': 2})
        for url in [self.add_url, self.update_url]:
            for quantity in ['0', '-1', '1.5', 'abc', '6', '', '999999999999999999999']:
                with self.subTest(url=url, quantity=quantity):
                    response = self.client.post(url, {'quantity': quantity})
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)
                    self.assertTrue(list(get_messages(response.wsgi_request)))
        self.client.post(self.add_url, {'quantity': 4})
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)

    def test_inactive_missing_and_out_of_stock(self):
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.post(self.add_url, {'quantity': 1}).status_code, 404)
        self.assertEqual(self.client.post(reverse('shop:cart_add', args=[999999]),
                                          {'quantity': 1}).status_code, 404)
        self.product.is_active = True
        self.product.stock = 0
        self.product.save()
        self.client.post(self.add_url, {'quantity': 1})
        self.assertNotIn(str(self.product.pk), self.client.session.get('cart', {}))

    def test_decimal_totals_and_current_price(self):
        self.client.post(self.add_url, {'quantity': 3})
        response = self.client.get(self.cart_url)
        self.assertEqual(response.context['total'], Decimal('0.30'))
        self.assertIsInstance(response.context['total'], Decimal)
        self.product.price = Decimal('0.20')
        self.product.save()
        self.assertEqual(self.client.get(self.cart_url).context['total'], Decimal('0.60'))

    def test_cart_rechecks_availability(self):
        self.client.post(self.add_url, {'quantity': 5})
        self.product.stock = 2
        self.product.save()
        response = self.client.get(self.cart_url)
        self.assertEqual(response.context['items'][0]['quantity'], 2)
        self.assertContains(response, 'уменьшено')
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.get(self.cart_url).context['items'], [])
        self.assertEqual(self.client.session['cart'], {})

    def test_deleted_product_is_removed(self):
        self.client.post(self.add_url, {'quantity': 1})
        self.product.delete()
        self.assertEqual(self.client.get(self.cart_url).context['items'], [])

    def test_update_unavailable_or_absent_product(self):
        self.client.post(self.update_url, {'quantity': 1})
        self.assertEqual(self.client.session.get('cart', {}), {})
        self.client.post(self.add_url, {'quantity': 1})
        self.product.is_active = False
        self.product.save()
        self.client.post(self.update_url, {'quantity': 1})
        self.assertEqual(self.client.session['cart'], {})

    def test_post_only_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        for url in [self.add_url, self.update_url, self.remove_url]:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(client.post(url, {'quantity': 1}).status_code, 403)
        response = client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertContains(response, 'csrfmiddlewaretoken')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(self.add_url, {'quantity': 1,
                                                    'csrfmiddlewaretoken': token}).status_code, 302)

    def test_sessions_are_independent(self):
        self.client.post(self.add_url, {'quantity': 1})
        self.assertContains(Client().get(self.cart_url), 'Корзина пуста.')

    def test_cart_loads_multiple_products_in_one_query(self):
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from shop.views import cart_detail

        second = Product.objects.create(name='Second', category=self.product.category,
                                        price='0.20', stock=3)
        hidden = Product.objects.create(name='Hidden', category=self.product.category,
                                        price=1, stock=5, is_active=False)
        request = RequestFactory().get(self.cart_url)
        request.user = AnonymousUser()
        request.session = {'cart': {str(self.product.pk): 2, str(second.pk): 4,
                                    str(hidden.pk): 1}}
        request._messages = FallbackStorage(request)
        with self.assertNumQueries(1):
            response = cart_detail(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session['cart'], {str(self.product.pk): 2, str(second.pk): 3})
        self.assertContains(response, '$0,80')
