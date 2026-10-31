from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include

from config import settings
from products.views import ProductList, ProductDetailsView
from shop.views import AccountView, RegisterView
from orders.views import CheckoutView

APPS_URLS =[
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('account/', AccountView.as_view(), name='account'),
    path('account/register/', RegisterView.as_view(), name='register'),
    path('account/login/', LoginView.as_view(template_name='shop/login.html'), name='login'),
    path('account/logout/', LogoutView.as_view(), name='logout'),
    path('cart/', include('shop.urls')),
    path('product/<slug:slug>/', ProductDetailsView.as_view(), name='product_detail'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('orders/', include('orders.urls', namespace = 'orders')),
    path('products/', include('products.urls', namespace = 'products')),
    path('reviews/', include('reviews.urls', namespace = 'reviews')),

    path('', ProductList.as_view(), name = 'product_list_main')

]

MEDIA_URLS = [
        #*static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
]

urlpatterns = APPS_URLS

if settings.DEBUG:
    urlpatterns += MEDIA_URLS
