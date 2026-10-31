from django.db.models import Avg, Q
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.serializers import ProductFilterSerializer, ProductSerializer
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
