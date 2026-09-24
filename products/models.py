from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Avg
from django.template.defaultfilters import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/products/category/{self.slug}'

    def get_update_url(self):
        return self.products.all()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField()
    price = models.DecimalField(decimal_places=2, max_digits=10,
                                validators=[MinValueValidator(0.0)])
    specifications = models.JSONField(default=dict, blank=True, null=True) # сделать логику заполнения специифкации с конкретными полями, заполняемыми в админке
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='products')
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_rating(self):
        if self.reviews.count() > 0:
            return self.reviews.aggregate(average=Avg('rating'))['average']
        else:
            return None

    def get_stars(self):
        rating = self.get_rating()
        if rating is None:
            return 0, False, 5

        rating = float(rating)
        full_stars = int(rating)
        has_half_star = (rating - full_stars) >= 0.5
        empty_stars = 5 - full_stars - int(has_half_star)
        return full_stars, has_half_star, empty_stars

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/products/{self.slug}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
