from django.db import models
from ckeditor.fields import RichTextField


class Category(models.Model):
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Адрес (slug)', max_length=255, unique=True)
    parent = models.ForeignKey('self', verbose_name='Родительская категория', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField('Изображение', upload_to='categories/', null=True, blank=True)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def descendant_ids(self):
        """id этой категории и всех вложенных подкатегорий"""
        ids = [self.id]
        frontier = [self.id]
        while frontier:
            frontier = list(
                Category.objects.filter(parent_id__in=frontier).values_list('id', flat=True))
            ids += frontier
        return ids


class Brand(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Адрес (slug)', unique=True)
    logo = models.ImageField('Логотип', upload_to='brands/', null=True, blank=True)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'бренд'
        verbose_name_plural = 'Бренды'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Адрес (slug)', max_length=255, unique=True)
    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, verbose_name='Бренд', on_delete=models.SET_NULL, null=True, blank=True)

    price = models.DecimalField('Цена, ₽', max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField('Количество на складе', default=0)

    description = RichTextField('Описание')
    specifications = models.JSONField('Характеристики', default=dict, blank=True)

    images = models.JSONField('Дополнительные изображения', default=list)
    main_image = models.ImageField('Главное изображение', upload_to='products/', null=True, blank=True)

    rating_avg = models.DecimalField('Средний рейтинг', max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField('Число оценок', default=0)

    is_active = models.BooleanField('Активен', default=True)
    is_featured = models.BooleanField('Рекомендуемый', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'Товары'
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
        verbose_name = 'характеристика'
        verbose_name_plural = 'Характеристики'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """Одно из допустимых значений атрибута, например "Красный" для атрибута "Цвет" """
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'значение характеристики'
        verbose_name_plural = 'Значения характеристик'
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
        verbose_name = 'характеристика товара'
        verbose_name_plural = 'Характеристики товаров'
        unique_together = ['product', 'attribute']

    def __str__(self):
        return f'{self.product.name} — {self.attribute.name}: {self.value.value}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.value_id and self.attribute_id and self.value.attribute_id != self.attribute_id:
            raise ValidationError({'value': 'Это значение принадлежит другому атрибуту'})
