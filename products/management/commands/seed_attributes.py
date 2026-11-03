from django.core.management.base import BaseCommand
from products.models import Category, Product, Attribute, AttributeValue, ProductAttributeValue


ATTRIBUTES = {
    'color': {
        'name': 'Цвет',
        'categories': [
            'smartphones', 'laptops', 'cases', 'mice', 'keyboards',
            'headphones', 'smartwatches', 'audio', 'accessories',
        ],
        'values': ['Чёрный', 'Белый', 'Серебристый', 'Серый', 'Синий', 'Фиолетовый', 'Красный', 'Золотой', 'Прозрачный'],
    },
    'ram': {
        'name': 'Оперативная память',
        'categories': ['smartphones', 'laptops'],
        'values': ['4 ГБ', '8 ГБ', '12 ГБ', '16 ГБ', '32 ГБ'],
    },
    'storage': {
        'name': 'Встроенная память',
        'categories': ['smartphones', 'laptops'],
        'values': ['64 ГБ', '128 ГБ', '256 ГБ', '512 ГБ', '1 ТБ'],
    },
}

# slug товара -> {slug_атрибута: значение}
PRODUCT_ATTRIBUTES = {
    'iphone-15-pro-128gb': {'color': 'Чёрный', 'storage': '128 ГБ'},
    'samsung-galaxy-s24': {'color': 'Фиолетовый', 'storage': '256 ГБ'},
    'xiaomi-redmi-note-13': {'color': 'Синий', 'storage': '128 ГБ'},
    'macbook-air-13-m2': {'color': 'Серебристый', 'ram': '8 ГБ', 'storage': '256 ГБ'},
    'samsung-galaxy-book4': {'color': 'Серый', 'ram': '16 ГБ', 'storage': '512 ГБ'},
    'sony-wh-1000xm5': {'color': 'Чёрный'},
    'apple-airpods-pro-2': {'color': 'Белый'},
    'logitech-mx-master-3s': {'color': 'Чёрный'},
    'logitech-mx-keys': {'color': 'Серый'},
    'apple-watch-series-9': {'color': 'Серебристый'},
    'xiaomi-smart-band-8': {'color': 'Чёрный'},
    'apple-silicone-case-iphone-15': {'color': 'Прозрачный'},
    'sony-srs-xb13': {'color': 'Синий'},
    'xiaomi-powerbank-20000': {'color': 'Белый'},
}


class Command(BaseCommand):
    help = 'Создаёт атрибуты-фильтры (цвет, память) и проставляет значения существующим демо-товарам'

    def handle(self, *args, **options):
        attribute_objs = {}
        value_objs = {}

        for attr_slug, cfg in ATTRIBUTES.items():
            attribute, created = Attribute.objects.get_or_create(
                slug=attr_slug,
                defaults={'name': cfg['name']}
            )
            if not created and attribute.name != cfg['name']:
                attribute.name = cfg['name']
                attribute.save()

            categories = Category.objects.filter(slug__in=cfg['categories'])
            attribute.categories.set(categories)

            attribute_objs[attr_slug] = attribute
            value_objs[attr_slug] = {}

            for val in cfg['values']:
                value_obj, _ = AttributeValue.objects.get_or_create(
                    attribute=attribute,
                    value=val,
                )
                value_objs[attr_slug][val] = value_obj

            self.stdout.write(self.style.SUCCESS(
                f'Атрибут "{cfg["name"]}" -> категории: {", ".join(cfg["categories"])}'
            ))

        assigned = 0
        skipped = 0
        for product_slug, attrs in PRODUCT_ATTRIBUTES.items():
            try:
                product = Product.objects.get(slug=product_slug)
            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Товар "{product_slug}" не найден, пропускаю'))
                skipped += 1
                continue

            for attr_slug, val in attrs.items():
                attribute = attribute_objs[attr_slug]
                value_obj = value_objs[attr_slug][val]

                ProductAttributeValue.objects.update_or_create(
                    product=product,
                    attribute=attribute,
                    defaults={'value': value_obj},
                )
                assigned += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Проставлено значений: {assigned}, пропущено товаров: {skipped}'
        ))
