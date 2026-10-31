from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views import ProductViewSet, OrderViewSet

router = DefaultRouter()
router.register('products', ProductViewSet, basename='api-product')
router.register('orders', OrderViewSet, basename='api-order')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny], authentication_classes=[]), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny], authentication_classes=[]), name='swagger-ui'),
    path('token/', extend_schema_view(post=extend_schema(summary='Получить JWT', description='Обмен имени пользователя и пароля на access и refresh.'))(TokenObtainPairView).as_view(), name='token_obtain_pair'),
    path('token/refresh/', extend_schema_view(post=extend_schema(summary='Обновить access-токен', description='Передайте действительный refresh-токен.'))(TokenRefreshView).as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
