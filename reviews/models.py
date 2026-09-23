from django.contrib.auth import get_user_model

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from products.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='reviews')
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    heading = models.CharField(max_length=100, blank=True)
    #body = models.TextField(blank=True, null=True)
    comment = models.TextField(max_length=1000, blank=True, null=True)
    image = models.ImageField(upload_to='reviews/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.owner} - {self.product}: {self.rating}'

    def get_absolute_url(self):
        return f'/reviews/{self.id}'

