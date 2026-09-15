from django.urls import path

from products.views import ProductList

urlpatterns = [
    path('', ProductList.as_view(), name='product_list'),
]