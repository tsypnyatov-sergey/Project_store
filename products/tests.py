from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from products.models import Category, Product


class ProductListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Hops')
        cls.other_category = Category.objects.create(name='Malts')
        cls.first = Product.objects.create(
            name='Citra', description='Fresh hops', price='10.00', category=cls.category)
        cls.second = Product.objects.create(
            name='Malt', description='Contains Citra', price='20.00', category=cls.other_category)
        cls.hidden = Product.objects.create(
            name='Hidden', description='Citra', price='5.00',
            category=cls.category, is_active=False)

    def get_products(self, **params):
        response = self.client.get(reverse('products:product_list'), params)
        self.assertEqual(response.status_code, 200)
        return list(response.context['products'])

    def test_active_products_and_search(self):
        self.assertCountEqual(self.get_products(search='Citra'), [self.first, self.second])
        self.assertNotIn(self.hidden, self.get_products())
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_category_and_price_filters(self):
        self.assertEqual(self.get_products(categories=self.category.slug), [self.first])
        self.assertEqual(self.get_products(min_price='10', max_price='10'), [self.first])
        self.assertEqual(self.get_products(min_price='11', max_price='20'), [self.second])
        self.assertEqual(self.get_products(search='missing'), [])

    def test_sorting(self):
        self.assertEqual(self.get_products(sorting='price'), [self.first, self.second])
        self.assertEqual(self.get_products(sorting='-price'), [self.second, self.first])
        self.assertEqual(self.get_products(sorting='-created_at'), [self.second, self.first])

    def test_popularity_counts_units_only_in_completed_payment_statuses(self):
        user = get_user_model().objects.create_user(username='buyer')
        for status, quantity in [('paid', 2), ('shipped', 3), ('delivered', 4)]:
            order = Order(owner=user, status=status)
            order.save()
            OrderItem.objects.create(order=order, product=self.first, quantity=quantity, price=10)
        for status in ['pending', 'canceled']:
            order = Order(owner=user, status=status)
            order.save()
            OrderItem.objects.create(order=order, product=self.second, quantity=100, price=20)
        products = self.get_products(sorting='popularity')
        self.assertEqual(products, [self.first, self.second])
        self.assertEqual(products[0].popularity, 9)
        self.assertEqual(products[1].popularity, 0)

    def test_invalid_filters_show_errors(self):
        for params in [dict(min_price='abc'), dict(min_price='-1'),
                       dict(max_price='NaN'), dict(max_price='Infinity'),
                       dict(min_price='30', max_price='10'),
                       dict(categories='missing'), dict(sorting='owner__password')]:
            with self.subTest(params=params):
                response = self.client.get(reverse('products:product_list'), params)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['filter_form'].errors)
                self.assertEqual(list(response.context['products']), [])

    def test_pagination_keeps_filters_and_handles_invalid_pages(self):
        for index in range(7):
            Product.objects.create(name=f'Citra {index}', description='Hops',
                                   price=10, category=self.category)
        params = dict(search='Citra', categories=self.category.slug,
                      min_price='0', max_price='30', sorting='price')
        response = self.client.get(reverse('products:product_list'), params)
        self.assertEqual(len(response.context['products']), 6)
        self.assertContains(response, 'page=2')
        self.assertContains(response, 'search=Citra')
        self.assertContains(response, 'categories=hops')
        self.assertContains(response, 'min_price=0')
        self.assertContains(response, 'max_price=30')
        self.assertContains(response, 'sorting=price')
        for page in ['bad', '0', '-1', '999']:
            self.assertEqual(self.client.get(reverse('products:product_list'),
                                             {**params, 'page': page}).status_code, 200)


class ProductDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Hops')
        cls.product = Product.objects.create(
            name='Citra', description='Fresh citrus hops', price='15.50',
            stock=7, category=cls.category)

    def test_active_product_details_without_image_or_reviews(self):
        url = reverse('product_detail', args=[self.product.slug])
        self.assertEqual(url, '/product/citra/')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/product_detail.html')
        for text in ['Citra', 'Fresh citrus hops', '15,50', 'Остаток: 7',
                     'Нет оценок', 'Изображение отсутствует']:
            self.assertContains(response, text)
        self.assertIsNone(response.context['average_rating'])
        self.assertContains(self.client.get('/products/'), 'href="/product/citra/"')

    def test_image_and_average_rating(self):
        from reviews.models import Review

        self.product.image = 'products/citra.jpg'
        self.product.save()
        for username, rating in [('first', 3), ('second', 4)]:
            user = get_user_model().objects.create_user(username=username)
            Review.objects.create(product=self.product, owner=user,
                                  rating=rating, comment=f'Review by {username}')
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.context['average_rating'], 3.5)
        self.assertEqual(response.context['reviews_count'], 2)
        self.assertTrue(response.context['has_half_star'])
        self.assertContains(response, self.product.image.url)
        self.assertContains(response, 'Review by first')
        self.assertContains(response, 'Review by second')
        self.assertNotContains(response, 'Нет оценок')

    def test_missing_and_inactive_products_return_404(self):
        self.assertEqual(self.client.get('/product/missing/').status_code, 404)
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.get('/product/citra/').status_code, 404)
        self.assertEqual(self.client.get('/products/citra/').status_code, 404)
