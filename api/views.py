from django.db.models import Avg, Q
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample, OpenApiResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.serializers import ProductFilterSerializer, ProductSerializer
from api.serializers import OrderCreateSerializer, OrderSerializer
from orders.models import Order, OrderStatus
from products.models import Product


@extend_schema_view(
    list=extend_schema(
        summary='Список активных товаров',
        description='Поиск по названию и описанию. Категория задаётся ID; цены неотрицательные. Некорректные фильтры возвращают 400.',
        parameters=[ProductFilterSerializer],
        responses={200: ProductSerializer(many=True), 400: OpenApiResponse(description='Ошибки параметров фильтрации')}),
    retrieve=extend_schema(summary='Информация о товаре', description='Только активные товары. Средний рейтинг равен null при отсутствии отзывов.',
                          responses={200: ProductSerializer, 404: OpenApiResponse(description='Товар не найден')})
)
class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.none()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        products = Product.objects.filter(is_active=True).annotate(
            average_rating=Avg('reviews__rating')).order_by('-created_at', '-pk')
        filters = ProductFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        data = filters.validated_data
        if data.get('category') is not None:
            products = products.filter(category=data['category'])
        if data.get('search'):
            products = products.filter(Q(name__icontains=data['search']) |
                                       Q(description__icontains=data['search']))
        if data.get('min_price') is not None:
            products = products.filter(price__gte=data['min_price'])
        if data.get('max_price') is not None:
            products = products.filter(price__lte=data['max_price'])
        return products


@extend_schema_view(
    list=extend_schema(summary='Мои заказы', description='Список только собственных заказов. Требуется JWT.'),
    retrieve=extend_schema(summary='Информация о моём заказе', description='Чужой или отсутствующий заказ возвращает 404.')
)
class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return Order.objects.filter(owner=self.request.user).prefetch_related('items').order_by('-created_at', '-pk')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @extend_schema(
        summary='Создать заказ',
        description='Непустой список уникальных товаров. Способ оплаты: cash — наличными, card — картой при получении. Автор, цены, итог и pending-статус определяются сервером; лишние поля клиента игнорируются.',
        request=OrderCreateSerializer,
        responses={201: OrderSerializer, 400: OpenApiResponse(description='Ошибки полей или недостаточный остаток'),
                   401: OpenApiResponse(description='Отсутствующий или недействительный JWT')},
        examples=[OpenApiExample('Заказ техники', request_only=True, value={
            'items': [{'product_id': 1, 'quantity': 2}],
            'shipping_address': 'Москва, улица Лесная, дом 1', 'payment_method': 'cash'})])
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = {str(item['product_id']): item['quantity'] for item in data['items']}
        try:
            order = Order.create_from_cart(request.user, cart, data['shipping_address'], data['payment_method'])
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary='Отменить мой заказ',
                   description='Разрешено только для собственного pending-заказа. Остатки восстанавливаются один раз. Повторная отмена возвращает 400.',
                   request=None, responses={200: OrderSerializer,
                       400: OpenApiResponse(description='Заказ нельзя отменить'),
                       401: OpenApiResponse(description='Требуется JWT'),
                       404: OpenApiResponse(description='Заказ не найден')})
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order.change_status(OrderStatus.CANCELLED, request.user, customer=True)
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response(OrderSerializer(order).data)
