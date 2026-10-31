from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from orders.models import Order, OrderItem, OrderStatus
from products.models import Category, Product
from reviews.models import Review


class ReviewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer')
        self.other = get_user_model().objects.create_user(username='other')
        category = Category.objects.create(name='Equipment')
        self.product = Product.objects.create(name='Machine', category=category, price=10)
        self.url = reverse('product_detail', args=[self.product.slug])
        self.data = {'rating': 5, 'heading': 'Отлично', 'comment': 'Хороший товар'}
        self.client.force_login(self.user)

    def purchase(self, owner=None, status=OrderStatus.DELIVERED, product=None):
        order = Order.objects.create(owner=owner or self.user, status=status)
        OrderItem.objects.create(order=order, product=product or self.product, quantity=1, price=10)
        return order

    def test_delivered_buyer_can_review_and_public_can_read(self):
        self.purchase()
        response = self.client.post(self.url, self.data, follow=True)
        self.assertContains(response, 'Ваш отзыв опубликован')
        review = Review.objects.get()
        self.assertEqual(review.owner, self.user)
        self.assertEqual(review.product, self.product)
        self.assertContains(Client().get(self.url), 'Хороший товар')
        self.assertEqual(response.context['average_rating'], 5)

    def test_anonymous_cannot_post(self):
        response = Client().post(self.url, self.data)
        self.assertRedirects(response, reverse('login') + '?next=' + self.url)
        self.assertFalse(Review.objects.exists())

    def test_purchase_required(self):
        self.purchase(owner=self.other)
        for status in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED]:
            self.purchase(status=status)
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'только после получения')
        self.assertFalse(Review.objects.exists())

    def test_other_product_purchase_does_not_count(self):
        other = Product.objects.create(name='Other', category=self.product.category, price=10)
        self.purchase(product=other)
        self.client.post(self.url, self.data)
        self.assertFalse(Review.objects.exists())

    def test_duplicate_rejected(self):
        self.purchase()
        self.client.post(self.url, self.data)
        response = self.client.post(self.url, {**self.data, 'rating': 1})
        self.assertContains(response, 'уже оставили отзыв')
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, 5)

    def test_invalid_ratings_and_model_validation(self):
        self.purchase()
        for rating in [0, 6, -1, '1.5', 'abc', '']:
            response = self.client.post(self.url, {**self.data, 'rating': rating})
            self.assertTrue(response.context['review_form'].errors)
            self.assertFalse(Review.objects.exists())
        for rating in [0, 6]:
            with self.assertRaises(ValidationError):
                Review(owner=self.user, product=self.product, rating=rating).full_clean()

    def test_database_constraints(self):
        Review.objects.create(owner=self.user, product=self.product, rating=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(owner=self.user, product=self.product, rating=5)
        for rating in [0, 6]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Review.objects.create(owner=self.other, product=self.product, rating=rating)

    def test_cannot_spoof_owner_or_product(self):
        self.purchase()
        self.client.post(self.url, {**self.data, 'owner': self.other.pk, 'product': 99999})
        self.assertEqual(Review.objects.get().owner, self.user)
        self.assertEqual(Review.objects.get().product, self.product)

    def test_csrf_and_inactive_product(self):
        self.purchase()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        self.product.is_active = False
        self.product.save()
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)
        self.assertFalse(Review.objects.exists())

    def test_average_and_no_ratings(self):
        self.assertContains(self.client.get(self.url), 'Нет оценок')
        Review.objects.create(owner=self.user, product=self.product, rating=1)
        Review.objects.create(owner=self.other, product=self.product, rating=4)
        self.assertEqual(self.client.get(self.url).context['average_rating'], 2.5)
