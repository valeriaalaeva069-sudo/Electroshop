from decimal import Decimal, InvalidOperation

from rest_framework import generics, filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Min, Max, ProtectedError
from django.shortcuts import get_object_or_404

from .models import Product, Category, Brand, Attribute
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    CategorySerializer,
    BrandSerializer,
    AdminProductSerializer,
    AdminProductCreateSerializer,
    AdminProductUpdateSerializer,
    CategoryFilterSerializer,
)
from users.permissions import IsAdminRole, is_shop_admin


def delete_product_safely(product):
    """Удаляет товар. Если его уже заказывали — только скрывает,
    иначе пропали бы позиции в истории заказов."""
    from orders.models import OrderItem
    if OrderItem.objects.filter(product=product).exists():
        product.is_active = False
        product.save(update_fields=['is_active'])
        return Response({
            'message': 'Товар деактивирован (есть связанные заказы)',
            'soft_delete': True,
        }, status=status.HTTP_200_OK)

    product.delete()
    return Response({
        'message': 'Товар удалён',
        'soft_delete': False,
    }, status=status.HTTP_200_OK)


# ============================================
# ПУБЛИЧНЫЕ ЭНДПОИНТЫ
# ============================================

class CategoryListView(generics.ListCreateAPIView):
    """Список категорий (GET) и создание (POST, только админ)"""
    queryset = Category.objects.filter(parent=None, is_active=True)
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [AllowAny()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали категории, обновление, удаление (админ)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminRole()]
        return [AllowAny()]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        try:
            category.delete()
        except ProtectedError:
            return Response(
                {'error': 'В категории (или её подкатегориях) есть товары, которые уже заказывали. '
                          'Удалить её нельзя — можно скрыть, выключив «Активна».'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryFiltersView(APIView):
    """Список фильтров (атрибут + допустимые значения) для категории —
    отдаётся боковой панели фильтров в каталоге. Возвращает только атрибуты,
    у которых среди активных товаров этой категории реально есть значения."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug, is_active=True)
        # у категории с подкатегориями фильтры собираются по всей ветке
        category_ids = category.descendant_ids()
        attributes = Attribute.objects.filter(categories__id__in=category_ids).distinct().order_by('order', 'name')
        serializer = CategoryFilterSerializer(
            attributes, many=True, context={'category_ids': category_ids}
        )
        data = [attr for attr in serializer.data if attr['values']]
        return Response(data)


class ProductFacetsView(APIView):
    """Данные для панели фильтров: бренды с числом товаров и границы цены.
    Считается по активным товарам, при необходимости — в одной категории."""
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.filter(is_active=True)
        category_slug = request.query_params.get('category_slug')
        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()
            products = products.filter(category_id__in=category.descendant_ids() if category else [])

        brands = (
            products.filter(brand__isnull=False)
            .values('brand__slug', 'brand__name')
            .annotate(count=Count('id'))
            .order_by('brand__name')
        )
        price = products.aggregate(min=Min('price'), max=Max('price'))
        return Response({
            'brands': [
                {'slug': b['brand__slug'], 'name': b['brand__name'], 'count': b['count']}
                for b in brands
            ],
            'price': {
                'min': int(price['min']) if price['min'] is not None else 0,
                'max': int(price['max']) if price['max'] is not None else 0,
            },
        })


class BrandListView(generics.ListCreateAPIView):
    """Список брендов (GET) и создание (POST, только админ)"""
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [AllowAny()]


class BrandDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали бренда, обновление, удаление (админ)"""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminRole()]
        return [AllowAny()]


class ProductListView(generics.ListCreateAPIView):
    """Список товаров с фильтрацией (GET) и создание (POST, только админ)"""
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'rating_avg', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')

        price_min = self._price_param('price_min')
        price_max = self._price_param('price_max')
        if price_min is not None:
            queryset = queryset.filter(price__gte=price_min)
        if price_max is not None:
            queryset = queryset.filter(price__lte=price_max)

        in_stock = self.request.query_params.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)

        category_slug = self.request.query_params.get('category_slug')
        if category_slug:
            category = Category.objects.filter(slug=category_slug).first()
            ids = category.descendant_ids() if category else []
            queryset = queryset.filter(category_id__in=ids)

        # Можно выбрать несколько брендов: ?brand_slug=apple&brand_slug=sony
        brand_slugs = [b for b in self.request.query_params.getlist('brand_slug') if b]
        if brand_slugs:
            queryset = queryset.filter(brand__slug__in=brand_slugs)

        # Фильтры по атрибутам: ?attr_color=3&attr_color=5&attr_ram=8
        # Внутри одного атрибута значения объединяются через ИЛИ,
        # между разными атрибутами — через И.
        has_attr_filter = False
        for key in self.request.query_params.keys():
            if not key.startswith('attr_'):
                continue
            attribute_slug = key[len('attr_'):]
            value_ids = self.request.query_params.getlist(key)
            if not value_ids:
                continue
            if not all(v.isdigit() for v in value_ids):
                raise ValidationError({key: 'Ожидаются числовые id значений'})
            has_attr_filter = True
            queryset = queryset.filter(
                attribute_values__attribute__slug=attribute_slug,
                attribute_values__value_id__in=value_ids,
            )

        if has_attr_filter:
            queryset = queryset.distinct()

        return queryset

    def _price_param(self, name):
        """Цена из query-параметра; мусор вроде ?price_min=abc — это 400, а не 500"""
        raw = self.request.query_params.get(name)
        if not raw:
            return None
        try:
            value = Decimal(raw)
        except InvalidOperation:
            raise ValidationError({name: 'Укажите число'})
        if not value.is_finite() or value < 0:
            raise ValidationError({name: 'Укажите неотрицательное число'})
        return value

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [AllowAny()]


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали товара, обновление, удаление (админ)"""
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        # Неактивные товары видит только админ; остальным — 404
        if is_shop_admin(self.request.user):
            return Product.objects.all()
        return Product.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminRole()]
        return [AllowAny()]

    def destroy(self, request, *args, **kwargs):
        return delete_product_safely(self.get_object())


# ============================================
# АДМИН: УПРАВЛЕНИЕ ТОВАРАМИ
# ============================================

class AdminProductListView(generics.ListCreateAPIView):
    """Список товаров и создание (админ)"""
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'price', 'stock_quantity', 'name']
    ordering = ['-created_at']
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminProductCreateSerializer
        return AdminProductSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category_id = serializer.validated_data.pop('category_id')
        brand_id = serializer.validated_data.pop('brand_id', None)

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response(
                {'error': 'Категория не найдена'},
                status=status.HTTP_400_BAD_REQUEST
            )

        brand = None
        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id)
            except Brand.DoesNotExist:
                return Response(
                    {'error': 'Бренд не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        product = Product.objects.create(
            category=category,
            brand=brand,
            **serializer.validated_data
        )

        return Response(
            AdminProductSerializer(product).data,
            status=status.HTTP_201_CREATED
        )


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали, обновление, удаление товара (админ)"""
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AdminProductUpdateSerializer
        return AdminProductSerializer

    def destroy(self, request, *args, **kwargs):
        return delete_product_safely(self.get_object())


class AdminCategoryListView(generics.ListCreateAPIView):
    """Список и создание категорий (админ)"""
    permission_classes = [IsAdminRole]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class AdminBrandListView(generics.ListCreateAPIView):
    """Список и создание брендов (админ)"""
    permission_classes = [IsAdminRole]
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
