from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from products.models import Category, Product


class UserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'StrongPass-67382!'
        cls.user = get_user_model().objects.create_user(username='buyer', password=cls.password)
        cls.other = get_user_model().objects.create_user(username='other', password=cls.password)
        cls.order = Order(owner=cls.user, shipping_address='Москва', payment_method='При получении')
        cls.order.save()
        cls.other_order = Order(owner=cls.other)
        cls.other_order.save()
        category = Category.objects.create(name='Equipment')
        cls.product = Product.objects.create(name='Machine', description='Equipment',
                                             category=category, price=100, stock=5)
        OrderItem.objects.create(order=cls.order, product=cls.product, price=90, quantity=2)

    def test_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbuyer', 'password1': self.password, 'password2': self.password})
        self.assertRedirects(response, reverse('login'))
        user = get_user_model().objects.get(username='newbuyer')
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_invalid_registration(self):
        for username, password2 in [('buyer', self.password), ('newbuyer', 'different')]:
            response = self.client.post(reverse('register'), {
                'username': username, 'password1': self.password, 'password2': password2})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_login_preserves_cart_and_changes_session_key(self):
        self.client.post(reverse('shop:cart_add', args=[self.product.pk]), {'quantity': 2})
        old_key = self.client.session.session_key
        response = self.client.post(reverse('login'), {'username': 'buyer', 'password': self.password})
        self.assertRedirects(response, reverse('account'))
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertEqual(self.client.session['cart'], {str(self.product.pk): 2})
        self.assertContains(self.client.get(reverse('account')), 'Выйти')

    def test_invalid_login(self):
        response = self.client.post(reverse('login'), {'username': 'buyer', 'password': 'wrong'})
        self.assertTrue(response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_anonymous_redirects(self):
        for url in [reverse('account'), reverse('orders:detail', args=[self.order.pk])]:
            self.assertRedirects(self.client.get(url), reverse('login') + '?next=' + url)

    def test_account_only_lists_own_orders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account'))
        self.assertEqual(list(response.context['orders']), [self.order])
        self.assertNotContains(response, reverse('orders:detail', args=[self.other_order.pk]))
        self.client.force_login(self.other)
        self.assertEqual(list(self.client.get(reverse('account')).context['orders']), [self.other_order])

    def test_own_order_and_foreign_or_missing_order(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('orders:detail', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Machine')
        self.assertContains(response, 'Москва')
        for pk in [self.other_order.pk, 999999]:
            self.assertEqual(self.client.get(reverse('orders:detail', args=[pk])).status_code, 404)

    def test_logout_is_post_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('product_list_main'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_csrf_required_for_authentication_forms(self):
        client = Client(enforce_csrf_checks=True)
        for name in ['register', 'login']:
            self.assertContains(client.get(reverse(name)), 'csrfmiddlewaretoken')
            self.assertEqual(client.post(reverse(name), {}).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('logout')).status_code, 403)

    def test_next_redirect_is_local(self):
        response = self.client.post(reverse('login'), {
            'username': 'buyer', 'password': self.password, 'next': 'https://example.com/'})
        self.assertRedirects(response, reverse('account'))
        self.client.post(reverse('logout'))
        response = self.client.post(reverse('login'), {
            'username': 'buyer', 'password': self.password,
            'next': reverse('orders:detail', args=[self.order.pk])})
        self.assertRedirects(response, reverse('orders:detail', args=[self.order.pk]))
