from rest_framework import serializers
from django.db.models import Count
from .models import Product, Category, Brand, Attribute, AttributeValue, ProductAttributeValue


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий (с вложенными подкатегориями)"""
    children = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image', 'description', 'parent', 'children', 'products_count', 'is_active']

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data

    def get_products_count(self, obj):
        # считаем товары и во вложенных подкатегориях
        return Product.objects.filter(category_id__in=obj.descendant_ids(), is_active=True).count()


class BrandSerializer(serializers.ModelSerializer):
    """Сериализатор для брендов"""
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'products_count', 'is_active']

    def get_products_count(self, obj):
        return obj.product_set.filter(is_active=True).count()


# ============================================
# ФИЛЬТРУЕМЫЕ АТРИБУТЫ (цвет, память и т.д.)
# ============================================

class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'value']


class AttributeSerializer(serializers.ModelSerializer):
    """Атрибут со всеми своими возможными значениями (для конструктора фильтров в админке)"""
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ['id', 'name', 'slug', 'order', 'values']


class CategoryFilterSerializer(serializers.ModelSerializer):
    """Атрибут + только те значения (с числом товаров), что реально встречаются
    среди товаров конкретной категории — отдаётся для панели фильтров в каталоге."""
    values = serializers.SerializerMethodField()

    class Meta:
        model = Attribute
        fields = ['id', 'name', 'slug', 'values']

    def get_values(self, obj):
        rows = (
            ProductAttributeValue.objects
            .filter(attribute=obj, product__category_id__in=self.context['category_ids'], product__is_active=True)
            .values('value_id', 'value__value', 'value__order')
            .annotate(count=Count('product', distinct=True))
            .order_by('value__order', 'value__value')
        )
        return [
            {'id': row['value_id'], 'value': row['value__value'], 'count': row['count']}
            for row in rows
        ]


class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """Значение конкретного товара по конкретному атрибуту (для карточки товара)"""
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    attribute_slug = serializers.CharField(source='attribute.slug', read_only=True)
    value = serializers.CharField(source='value.value', read_only=True)

    class Meta:
        model = ProductAttributeValue
        fields = ['attribute_name', 'attribute_slug', 'value']


class ProductListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка товаров"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    main_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'main_image', 'main_image_url',
            'rating_avg', 'rating_count', 'in_stock', 'stock_quantity',
            'category_name', 'brand_name', 'is_featured', 'created_at'
        ]

    def get_main_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о товаре"""
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    attributes = ProductAttributeValueSerializer(source='attribute_values', many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления товара (админ)"""

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'category', 'brand',
            'price', 'stock_quantity', 'description',
            'specifications', 'images', 'main_image',
            'is_active', 'is_featured'
        ]


class AdminProductSerializer(serializers.ModelSerializer):
    """Сериализатор для управления товарами (админ)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    main_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'category', 'category_name',
            'brand', 'brand_name', 'price', 'stock_quantity',
            'description', 'specifications',
            'main_image', 'main_image_url', 'images',
            'rating_avg', 'rating_count', 'is_active', 'is_featured',
            'in_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'rating_avg', 'rating_count', 'created_at', 'updated_at']

    def get_main_image_url(self, obj):
        if obj.main_image:
            return obj.main_image.url
        return None


class AdminProductCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания товара (админ)"""
    category_id = serializers.IntegerField(write_only=True)
    brand_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'category_id', 'brand_id',
            'price', 'stock_quantity', 'description',
            'specifications', 'main_image',
            'is_active', 'is_featured'
        ]

    def validate_slug(self, value):
        if Product.objects.filter(slug=value).exists():
            raise serializers.ValidationError('Товар с таким slug уже существует')
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value


class AdminProductUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления товара (админ)"""
    category_id = serializers.IntegerField(write_only=True, required=False)
    brand_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'category_id', 'brand_id',
            'price', 'stock_quantity', 'description',
            'specifications', 'main_image',
            'is_active', 'is_featured'
        ]

    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        brand_id = validated_data.pop('brand_id', None)

        if category_id:
            try:
                instance.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError({'category_id': 'Категория не найдена'})

        if brand_id is not None:
            if brand_id:
                try:
                    instance.brand = Brand.objects.get(id=brand_id)
                except Brand.DoesNotExist:
                    raise serializers.ValidationError({'brand_id': 'Бренд не найден'})
            else:
                instance.brand = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
