from django.db.models import Avg, Q
from rest_framework.permissions import AllowAny
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


class ProductViewSet(ReadOnlyModelViewSet):
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


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user).prefetch_related('items').order_by('-created_at', '-pk')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order.change_status(OrderStatus.CANCELLED, request.user, customer=True)
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response(OrderSerializer(order).data)
