

from django.shortcuts import render
from django.views.generic import ListView

from products.models import Product


# Create your views here.
class ProductList(ListView):
    model = Product
    context_object_name = 'products'
    template_name = 'products/product_list.html'