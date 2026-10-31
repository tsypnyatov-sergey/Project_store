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
