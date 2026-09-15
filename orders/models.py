from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from products.models import Product


class OrderStatus(models.TextChoices):
    PENDING = 'pending'
    PAID = 'paid'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'canceled'

class Order(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    status = models.CharField(max_length=10,choices=OrderStatus.choices,
                              default=OrderStatus.PENDING)
    payment_method = models.CharField(max_length=100)
    shipping_address = models.CharField(max_length=255)
    total_price = models.DecimalField(null=True,max_digits=10, decimal_places=2,
                                      validators=[MinValueValidator(0.0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.owner} - {self.status}'

    def get_absolute_url(self):
        return f'/orders/{self.id}/'



    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.total_price = self.get_total_price()
        super().save(*args, **kwargs)

    def get_total_price(self):
        return sum([item.price * item.quantity for item in self.items.all()])



    class Meta:
        verbose_name_plural = 'Orders'
        verbose_name = 'Order'
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0.0)])
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'{self.order} - {self.quantity}'

    class Meta:
        verbose_name_plural = 'Order Items'
        verbose_name = 'Order Item'
        ordering = ['-created_at']