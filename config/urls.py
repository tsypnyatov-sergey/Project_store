from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from config import settings
from products.views import ProductList

APPS_URLS =[
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