from django.urls import path

from orders.views import OrderDetailView, cancel_order

app_name = 'orders'
urlpatterns = [
    path('<int:pk>/', OrderDetailView.as_view(), name='detail'),
    path('<int:pk>/cancel/', cancel_order, name='cancel'),
]
