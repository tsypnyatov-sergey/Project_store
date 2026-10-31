from rest_framework import serializers

from products.models import Category, Product
from orders.models import Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'category',
                  'image', 'stock', 'specifications', 'created_at', 'average_rating']


class ProductFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    def validate(self, attrs):
        minimum = attrs.get('min_price')
        maximum = attrs.get('max_price')
        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError({'max_price': 'Максимальная цена меньше минимальной.'})
        return attrs


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    quantity = serializers.IntegerField(min_value=1, max_value=2147483647)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, allow_empty=False)
    shipping_address = serializers.CharField(max_length=255)
    payment_method = serializers.ChoiceField(choices=['cash', 'card'])

    def validate_items(self, items):
        product_ids = [item['product_id'] for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError('Один товар нельзя указывать несколько раз.')
        return items


class OrderItemSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product_id', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'payment_method', 'shipping_address',
                  'total_price', 'created_at', 'items']
