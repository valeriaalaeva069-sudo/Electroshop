from django.core.management import call_command
from django.core.management.base import BaseCommand

from products.models import Brand, Category

# slug -> (название, slug родителя)
CATEGORIES = {
    'smartphones': ('Смартфоны', None),
    'laptops': ('Ноутбуки', None),
    'accessories': ('Аксессуары', None),
    'audio': ('Аудио', None),
    'smartwatches': ('Умные часы', None),
    'mice': ('Мышки', 'accessories'),
    'keyboards': ('Клавиатуры', 'accessories'),
    'cases': ('Чехлы', 'accessories'),
    'headphones': ('Наушники', 'audio'),
}

# Бренды, на которые ссылается seed_products (остальные добавит seed_catalog)
BASE_BRANDS = {
    'apple': 'Apple',
    'samsung': 'Samsung',
    'xiaomi': 'Xiaomi',
    'sony': 'Sony',
    'logitech': 'Logitech',
}


class Command(BaseCommand):
    help = ('Наполняет пустую базу демо-данными: категории, бренды, товары и фильтры. '
            'Существующие записи не меняет, запускать можно повторно.')

    def handle(self, *args, **options):
        created_cats = 0
        for slug, (name, _parent) in CATEGORIES.items():
            _, created = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            created_cats += created
        # родителей проставляем вторым проходом, когда все категории уже есть
        for slug, (_name, parent_slug) in CATEGORIES.items():
            if parent_slug:
                Category.objects.filter(slug=slug, parent__isnull=True).update(
                    parent=Category.objects.get(slug=parent_slug))

        created_brands = 0
        for slug, name in BASE_BRANDS.items():
            _, created = Brand.objects.get_or_create(slug=slug, defaults={'name': name})
            created_brands += created

        self.stdout.write(self.style.SUCCESS(
            f'Категорий создано: {created_cats}, брендов создано: {created_brands}'))

        call_command('seed_products', stdout=self.stdout)
        call_command('seed_catalog', stdout=self.stdout)
