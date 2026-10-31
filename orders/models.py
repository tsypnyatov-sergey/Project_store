from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

from products.models import Product


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Ожидает оплаты'
    PAID = 'paid', 'Оплачен'
    SHIPPED = 'shipped', 'Отправлен'
    DELIVERED = 'delivered', 'Доставлен'
    CANCELLED = 'cancelled', 'Отменён'


class Order(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    payment_method = models.CharField(max_length=100)
    shipping_address = models.CharField(max_length=255)
    total_price = models.DecimalField(default=Decimal('0.00'), max_digits=10, decimal_places=2,
                                     validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.owner} - {self.status}'

    def get_absolute_url(self):
        return f'/orders/{self.pk}/'

    def get_total_price(self):
        return sum((item.price * item.quantity for item in self.items.all()), Decimal('0.00'))

    @classmethod
    @transaction.atomic
    def create_from_cart(cls, owner, cart, shipping_address, payment_method):
        if not isinstance(cart, dict) or not cart:
            raise ValidationError('Корзина пуста.')
        quantities = {}
        for product_id, quantity in cart.items():
            if not str(product_id).isdigit() or type(quantity) is not int or quantity <= 0:
                raise ValidationError('Некорректный товар или количество.')
            product_id = int(product_id)
            if product_id <= 0 or product_id > 9223372036854775807 or product_id in quantities:
                raise ValidationError('Некорректный товар.')
            quantities[product_id] = quantity
        products = list(Product.objects.select_for_update().filter(pk__in=quantities).order_by('pk'))
        if len(products) != len(quantities):
            raise ValidationError('Один из товаров больше не существует.')
        total = Decimal('0.00')
        for product in products:
            quantity = quantities[product.pk]
            if not product.is_active or quantity > product.stock:
                raise ValidationError(f'Товар «{product.name}» недоступен в нужном количестве.')
            total += product.price * quantity
        order = cls(owner=owner, shipping_address=shipping_address,
                    payment_method=payment_method, total_price=total)
        order.full_clean()
        order.save()
        for product in products:
            quantity = quantities[product.pk]
            OrderItem.objects.create(order=order, product=product, quantity=quantity, price=product.price)
            product.stock -= quantity
            product.save(update_fields=['stock'])
        return order

    def validate_transition(self, status):
        transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
        }
        if status not in transitions.get(self.status, []):
            raise ValidationError('Такое изменение статуса заказа запрещено.')

    @transaction.atomic
    def change_status(self, status, user, customer=False):
        order = Order.objects.select_for_update().get(pk=self.pk)
        if (customer or not user.is_staff) and (order.owner_id != user.pk or
                                  order.status != OrderStatus.PENDING or status != OrderStatus.CANCELLED):
            raise ValidationError('Вы можете отменить только свой заказ, ожидающий оплаты.')
        order.validate_transition(status)
        if status == OrderStatus.CANCELLED:
            items = list(order.items.all())
            products = Product.objects.select_for_update().filter(
                pk__in=[item.product_id for item in items]).order_by('pk')
            quantities = {item.product_id: item.quantity for item in items}
            for product in products:
                product.stock += quantities[product.pk]
                product.save(update_fields=['stock'])
        order.status = status
        order.save(update_fields=['status', 'updated_at'])
        self.status = status

    class Meta:
        verbose_name_plural = 'Orders'
        verbose_name = 'Order'
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(total_price__gte=0), name='order_total_nonnegative')]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.order} - {self.quantity}'

    class Meta:
        verbose_name_plural = 'Позиции заказа'
        verbose_name = 'Позиция заказа'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['order', 'product'], name='unique_order_product'),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='orderitem_quantity_positive'),
            models.CheckConstraint(condition=models.Q(price__gte=0), name='orderitem_price_nonnegative'),
        ]
