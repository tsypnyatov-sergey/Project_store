from django.urls import path

from products.views import ProductList, GuidesReceiptView, ProductDetailsView

app_name = 'products'

urlpatterns = [
    path('', ProductList.as_view(), name='product_list'),
    path('guides-recipes/', GuidesReceiptView.as_view(), name='guides-recipes'),
    path('<slug:slug>/',ProductDetailsView.as_view(), name='product_detail'),


]
