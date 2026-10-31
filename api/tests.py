from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from products.models import Category, Product
from reviews.models import Review


class ProductAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Equipment')
        other = Category.objects.create(name='Parts')
        cls.first = Product.objects.create(name='Machine', description='Forest equipment',
                                          category=cls.category, price='10.00')
        cls.second = Product.objects.create(name='Part', description='For Machine',
                                           category=other, price='20.00')
        cls.hidden = Product.objects.create(name='Hidden', category=other,
                                           price=1, is_active=False)

    def test_public_list_and_details(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual({p['id'] for p in response.data['results']}, {self.first.pk, self.second.pk})
        response = self.client.get(f'/api/products/{self.first.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Machine')
        self.assertIsNone(response.data['average_rating'])
        for pk in [self.hidden.pk, 999999]:
            self.assertEqual(self.client.get(f'/api/products/{pk}/').status_code, 404)

    def test_filters_and_or_search(self):
        for params, ids in [({'search': 'Machine'}, {self.first.pk, self.second.pk}),
                            ({'search': 'Forest'}, {self.first.pk}),
                            ({'category': self.category.pk}, {self.first.pk}),
                            ({'min_price': '10', 'max_price': '10'}, {self.first.pk}),
                            ({'min_price': '11', 'max_price': '20'}, {self.second.pk}),
                            ({'search': 'missing'}, set())]:
            response = self.client.get('/api/products/', params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual({p['id'] for p in response.data['results']}, ids)

    def test_invalid_filters(self):
        for params in [{'category': 'bad'}, {'category': 999999}, {'min_price': -1},
                       {'min_price': 'abc'}, {'max_price': 'NaN'}, {'max_price': 'Infinity'},
                       {'min_price': 30, 'max_price': 10}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/products/', params).status_code, 400)
        self.assertEqual(self.client.get('/api/products/', {'page': 'bad'}).status_code, 404)

    def test_pagination_keeps_filters(self):
        for index in range(7):
            Product.objects.create(name=f'Machine {index}', category=self.category, price=10)
        response = self.client.get('/api/products/', {'search': 'Machine', 'category': self.category.pk})
        self.assertEqual(len(response.data['results']), 6)
        self.assertIn('search=Machine', response.data['next'])
        second = self.client.get(response.data['next'])
        self.assertEqual(len(second.data['results']), 2)
        self.assertFalse({p['id'] for p in response.data['results']} & {p['id'] for p in second.data['results']})

    def test_average_rating(self):
        for name, rating in [('first', 2), ('second', 5)]:
            user = get_user_model().objects.create_user(username=name)
            Review.objects.create(owner=user, product=self.first, rating=rating)
        response = self.client.get(f'/api/products/{self.first.pk}/')
        self.assertEqual(response.data['average_rating'], 3.5)
        results = self.client.get('/api/products/').data['results']
        self.assertEqual(next(p['average_rating'] for p in results if p['id'] == self.first.pk), 3.5)

    def test_writes_forbidden_even_for_admin(self):
        admin = get_user_model().objects.create_superuser(username='admin', password='Secret-7482!')
        for authenticated in [False, True]:
            if authenticated:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = str(RefreshToken.for_user(admin).access_token)
                self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
            for method in ['post', 'put', 'patch', 'delete']:
                for url in ['/api/products/', f'/api/products/{self.first.pk}/']:
                    self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 405)
        self.assertEqual(Product.objects.count(), 3)


class JWTTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Strong-Password-93857!'
        cls.user = get_user_model().objects.create_user(username='buyer', password=cls.password)

    def test_obtain_and_refresh(self):
        response = self.client.post('/api/token/', {'username': 'buyer', 'password': self.password})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(str(AccessToken(response.data['access'])['user_id']), str(self.user.pk))
        refreshed = self.client.post('/api/token/refresh/', {'refresh': response.data['refresh']})
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(str(AccessToken(refreshed.data['access'])['user_id']), str(self.user.pk))
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + refreshed.data['access'])
        self.assertEqual(self.client.get('/api/products/').status_code, 200)

    def test_wrong_credentials_and_missing_fields(self):
        self.assertEqual(self.client.post('/api/token/', {'username': 'buyer', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.client.post('/api/token/', {}).status_code, 400)
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': 'bad'}).status_code, 401)
        self.assertEqual(self.client.post('/api/token/refresh/', {}).status_code, 400)

    def test_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.post('/api/token/', {'username': 'buyer', 'password': self.password}).status_code, 401)

    def test_api_does_not_authenticate_browser_session(self):
        from rest_framework.permissions import IsAuthenticated
        from rest_framework.response import Response
        from rest_framework.views import APIView
        from rest_framework.test import APIRequestFactory

        class ProtectedView(APIView):
            permission_classes = [IsAuthenticated]

            def get(self, request):
                return Response({'user': request.user.pk})

        self.client.force_login(self.user)
        factory = APIRequestFactory()
        request = factory.get('/')
        request.session = self.client.session
        request.user = self.user
        self.assertEqual(ProtectedView.as_view()(request).status_code, 401)
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)
        request = factory.get('/', HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(ProtectedView.as_view()(request).status_code, 200)


class OrderAPITests(APITestCase):
    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user = get_user_model().objects.create_user(username='buyer')
        self.other = get_user_model().objects.create_user(username='other')
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)
        category = Category.objects.create(name='Equipment')
        self.product = Product.objects.create(name='Machine', category=category, price='10.25', stock=5)
        self.payload = {'items': [{'product_id': self.product.pk, 'quantity': 2}],
                        'shipping_address': 'Москва, дом 1', 'payment_method': 'cash'}

    def create_order(self, owner=None, status='pending'):
        from orders.models import Order
        order = Order.create_from_cart(owner or self.user, {str(self.product.pk): 1}, 'Москва', 'cash')
        if status != 'pending':
            Order.objects.filter(pk=order.pk).update(status=status)
            order.refresh_from_db()
        return order

    def test_all_operations_require_valid_jwt(self):
        order = self.create_order()
        for header in ['', 'Bearer invalid']:
            self.client.credentials(HTTP_AUTHORIZATION=header)
            for method, url in [('get', '/api/orders/'), ('post', '/api/orders/'),
                                ('get', f'/api/orders/{order.pk}/'),
                                ('post', f'/api/orders/{order.pk}/cancel/')]:
                self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 401)
        self.client.credentials()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/orders/').status_code, 401)

    def test_only_own_orders_visible(self):
        order = self.create_order()
        foreign = self.create_order(owner=self.other)
        response = self.client.get('/api/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([o['id'] for o in response.data['results']], [order.pk])
        detail = self.client.get(f'/api/orders/{order.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['items'][0]['product_id'], self.product.pk)
        self.assertEqual(self.client.get(f'/api/orders/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/orders/{foreign.pk}/cancel/').status_code, 404)
        self.assertEqual(self.client.get('/api/orders/999999/').status_code, 404)

    def test_create_uses_database_prices_and_preserves_session_cart(self):
        from orders.models import Order
        session = self.client.session
        session['cart'] = {str(self.product.pk): 4}
        session.save()
        payload = {**self.payload, 'user_id': self.other.pk, 'owner': self.other.pk,
                   'total_price': '0.01', 'status': 'paid', 'price': '0.01'}
        payload['items'] = [{'product_id': self.product.pk, 'quantity': 2,
                             'unit_price': '0.01', 'price': '0.01'}]
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.owner, self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(str(order.total_price), '20.50')
        self.assertEqual(str(order.items.get().price), '10.25')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.client.session['cart'], {str(self.product.pk): 4})

    def test_create_without_browser_session(self):
        response = self.client.post('/api/orders/', self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['total_price'], '20.50')

    def test_invalid_input_rejected(self):
        from orders.models import Order
        variants = [dict(self.payload, items=[]), dict(self.payload, items=self.payload['items'] * 2),
                    dict(self.payload, payment_method='bitcoin'), dict(self.payload, shipping_address=''), {}]
        for quantity in [0, -1, 'abc', 1.5, None, True]:
            variants.append(dict(self.payload, items=[{'product_id': self.product.pk, 'quantity': quantity}]))
        for payload in variants:
            with self.subTest(payload=payload):
                response = self.client.post('/api/orders/', payload, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_missing_inactive_and_insufficient_products(self):
        from orders.models import Order, OrderItem
        for pk, quantity, active in [(999999, 1, True), (self.product.pk, 6, True), (self.product.pk, 1, False)]:
            self.product.is_active = active
            self.product.save()
            response = self.client.post('/api/orders/', dict(self.payload, items=[{'product_id': pk, 'quantity': quantity}]), format='json')
            self.assertEqual(response.status_code, 400)
            self.assertFalse(Order.objects.exists())
            self.assertFalse(OrderItem.objects.exists())
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, 5)

    def test_mixed_valid_and_invalid_items_do_not_create_partial_order(self):
        from orders.models import Order, OrderItem
        payload = dict(self.payload, items=self.payload['items'] + [{'product_id': 999999, 'quantity': 1}])
        self.assertEqual(self.client.post('/api/orders/', payload, format='json').status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_cancel_restores_stock_only_once(self):
        order = self.create_order()
        url = f'/api/orders/{order.pk}/cancel/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(self.client.post(url).status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_nonpending_cancel_rejected_even_for_staff(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user.is_staff = True
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(self.user).access_token))
        for status in ['paid', 'shipped', 'delivered']:
            order = self.create_order(status=status)
            self.product.refresh_from_db()
            stock = self.product.stock
            self.assertEqual(self.client.post(f'/api/orders/{order.pk}/cancel/').status_code, 400)
            order.refresh_from_db()
            self.assertEqual(order.status, status)
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, stock)

    def test_put_patch_delete_not_available(self):
        order = self.create_order()
        for method in ['put', 'patch', 'delete']:
            for url in ['/api/orders/', f'/api/orders/{order.pk}/']:
                self.assertEqual(getattr(self.client, method)(url, {}, format='json').status_code, 405)
        self.assertEqual(self.client.get(f'/api/orders/{order.pk}/cancel/').status_code, 405)
