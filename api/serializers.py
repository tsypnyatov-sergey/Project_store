from rest_framework import serializers

from products.models import Category, Product


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
