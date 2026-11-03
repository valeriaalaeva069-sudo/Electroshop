from django.contrib import admin
from .models import Category, Brand, Product, Attribute, AttributeValue, ProductAttributeValue
from .forms import ProductForm, CategoryForm, BrandForm


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ['name', 'parent', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    form = BrandForm
    list_display = ['name', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


class ProductAttributeValueInline(admin.TabularInline):
    """Позволяет прямо на странице товара задать его характеристики-фильтры
    (цвет, память и т.д.) — появляется внизу формы товара."""
    model = ProductAttributeValue
    extra = 1
    autocomplete_fields = ['attribute', 'value']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ['name', 'price', 'stock_quantity', 'in_stock_flag', 'is_active']
    list_filter = ['category', 'brand', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductAttributeValueInline]

    @admin.display(boolean=True, description='В наличии')
    def in_stock_flag(self, obj):
        return obj.in_stock


class AttributeValueInline(admin.TabularInline):
    """Позволяет сразу на странице атрибута ("Цвет") добавить его значения
    ("Красный", "Чёрный", ...), не заходя в отдельный раздел."""
    model = AttributeValue
    extra = 3


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'categories_list']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['categories']
    inlines = [AttributeValueInline]
    search_fields = ['name']

    def categories_list(self, obj):
        return ', '.join(c.name for c in obj.categories.all())
    categories_list.short_description = 'Категории'


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ['value', 'attribute']
    list_filter = ['attribute']
    search_fields = ['value']
