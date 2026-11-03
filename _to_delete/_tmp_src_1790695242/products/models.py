from django.db import models
from ckeditor.fields import RichTextField


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)

    description = RichTextField()
    specifications = models.JSONField(default=dict, blank=True)

    images = models.JSONField(default=list)
    main_image = models.ImageField(upload_to='products/', null=True, blank=True)

    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def in_stock(self):
        return self.stock_quantity > 0


# ============================================
# ФИЛЬТРУЕМЫЕ АТРИБУТЫ ТОВАРОВ (цвет, объём памяти и т.д.)
# ============================================
# Один Attribute (например "Цвет") может относиться к нескольким категориям
# (телефоны, ноутбуки, чехлы — у всех может быть цвет). Конкретные допустимые
# значения задаются через AttributeValue, чтобы фильтр в каталоге собирал их
# в чекбоксы без опечаток/разнобоя ("красный" / "Красный" / "red").

class Attribute(models.Model):
    """Характеристика-фильтр, например «Цвет» или «Оперативная память»"""
    name = models.CharField(max_length=100, help_text='Название, которое увидит покупатель, например "Цвет"')
    slug = models.SlugField(unique=True, help_text='Латиницей, для URL/фильтров, например "color"')
    categories = models.ManyToManyField(
        Category,
        related_name='attributes',
        blank=True,
        help_text='В каких категориях показывать этот фильтр'
    )
    order = models.PositiveIntegerField(default=0, help_text='Порядок отображения (меньше — выше)')

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """Одно из допустимых значений атрибута, например "Красный" для атрибута "Цвет" """
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['attribute', 'value']
        ordering = ['order', 'value']

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'


class ProductAttributeValue(models.Model):
    """Связь «у этого товара атрибут X равен значению Y»"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='product_values')
    value = models.ForeignKey(AttributeValue, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['product', 'attribute']

    def __str__(self):
        return f'{self.product.name} — {self.attribute.name}: {self.value.value}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.value_id and self.attribute_id and self.value.attribute_id != self.attribute_id:
            raise ValidationError({'value': 'Это значение принадлежит другому атрибуту'})
