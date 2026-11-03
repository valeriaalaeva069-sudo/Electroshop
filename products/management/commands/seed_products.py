from django.core.management.base import BaseCommand
from products.models import Category, Brand, Product


PRODUCTS = [
    {
        'name': 'iPhone 15 Pro 128GB',
        'slug': 'iphone-15-pro-128gb',
        'category': 'smartphones',
        'brand': 'apple',
        'price': 89990,
        'stock_quantity': 15,
        'description': 'Флагманский смартфон Apple с чипом A17 Pro и титановым корпусом.',
        'specifications': {'Память': '128 ГБ', 'Экран': '6.1" OLED', 'Процессор': 'A17 Pro', 'Камера': '48 Мп'},
        'is_featured': True,
    },
    {
        'name': 'Samsung Galaxy S24',
        'slug': 'samsung-galaxy-s24',
        'category': 'smartphones',
        'brand': 'samsung',
        'price': 74990,
        'stock_quantity': 20,
        'description': 'Мощный Android-флагман с ярким AMOLED-экраном и AI-функциями.',
        'specifications': {'Память': '256 ГБ', 'Экран': '6.2" AMOLED', 'Процессор': 'Snapdragon 8 Gen 3'},
        'is_featured': True,
    },
    {
        'name': 'Xiaomi Redmi Note 13',
        'slug': 'xiaomi-redmi-note-13',
        'category': 'smartphones',
        'brand': 'xiaomi',
        'price': 21990,
        'stock_quantity': 30,
        'description': 'Доступный смартфон с большим экраном и быстрой зарядкой.',
        'specifications': {'Память': '128 ГБ', 'Экран': '6.67" AMOLED', 'Зарядка': '33 Вт'},
    },
    {
        'name': 'MacBook Air 13" M2',
        'slug': 'macbook-air-13-m2',
        'category': 'laptops',
        'brand': 'apple',
        'price': 114990,
        'stock_quantity': 8,
        'description': 'Тонкий и лёгкий ноутбук на чипе Apple M2 с батареей до 18 часов.',
        'specifications': {'Процессор': 'Apple M2', 'ОЗУ': '8 ГБ', 'SSD': '256 ГБ', 'Экран': '13.6"'},
        'is_featured': True,
    },
    {
        'name': 'Samsung Galaxy Book4',
        'slug': 'samsung-galaxy-book4',
        'category': 'laptops',
        'brand': 'samsung',
        'price': 79990,
        'stock_quantity': 10,
        'description': 'Компактный ноутбук для работы и учёбы на процессоре Intel Core.',
        'specifications': {'Процессор': 'Intel Core i5', 'ОЗУ': '16 ГБ', 'SSD': '512 ГБ'},
    },
    {
        'name': 'Sony WH-1000XM5',
        'slug': 'sony-wh-1000xm5',
        'category': 'headphones',
        'brand': 'sony',
        'price': 34990,
        'stock_quantity': 12,
        'description': 'Беспроводные наушники с лучшим в классе шумоподавлением.',
        'specifications': {'Тип': 'Полноразмерные', 'Автономность': '30 часов', 'Шумоподавление': 'Да'},
        'is_featured': True,
    },
    {
        'name': 'Apple AirPods Pro 2',
        'slug': 'apple-airpods-pro-2',
        'category': 'headphones',
        'brand': 'apple',
        'price': 24990,
        'stock_quantity': 25,
        'description': 'Компактные беспроводные наушники с активным шумоподавлением.',
        'specifications': {'Тип': 'Вкладыши', 'Автономность': '6 часов', 'Шумоподавление': 'Да'},
    },
    {
        'name': 'Logitech MX Master 3S',
        'slug': 'logitech-mx-master-3s',
        'category': 'mice',
        'brand': 'logitech',
        'price': 8990,
        'stock_quantity': 18,
        'description': 'Эргономичная беспроводная мышь для профессиональной работы.',
        'specifications': {'Тип': 'Беспроводная', 'DPI': '8000', 'Подключение': 'Bluetooth / USB'},
    },
    {
        'name': 'Logitech MX Keys',
        'slug': 'logitech-mx-keys',
        'category': 'keyboards',
        'brand': 'logitech',
        'price': 10990,
        'stock_quantity': 14,
        'description': 'Беспроводная клавиатура с подсветкой и тихими клавишами.',
        'specifications': {'Тип': 'Беспроводная', 'Подсветка': 'Да', 'Раскладка': 'RU/EN'},
    },
    {
        'name': 'Apple Watch Series 9',
        'slug': 'apple-watch-series-9',
        'category': 'smartwatches',
        'brand': 'apple',
        'price': 41990,
        'stock_quantity': 10,
        'description': 'Умные часы с большим ярким экраном и функциями здоровья.',
        'specifications': {'Экран': 'Retina OLED', 'Водозащита': 'Да', 'Автономность': '18 часов'},
    },
    {
        'name': 'Xiaomi Smart Band 8',
        'slug': 'xiaomi-smart-band-8',
        'category': 'smartwatches',
        'brand': 'xiaomi',
        'price': 3490,
        'stock_quantity': 40,
        'description': 'Лёгкий фитнес-браслет с долгим временем автономной работы.',
        'specifications': {'Экран': 'AMOLED', 'Автономность': '16 дней', 'Водозащита': '5 АТМ'},
    },
    {
        'name': 'Чехол Apple Silicone Case для iPhone 15',
        'slug': 'apple-silicone-case-iphone-15',
        'category': 'cases',
        'brand': 'apple',
        'price': 3990,
        'stock_quantity': 50,
        'description': 'Оригинальный силиконовый чехол с мягкой подкладкой из микрофибры.',
        'specifications': {'Материал': 'Силикон', 'Совместимость': 'iPhone 15'},
    },
    {
        'name': 'Sony SRS-XB13',
        'slug': 'sony-srs-xb13',
        'category': 'audio',
        'brand': 'sony',
        'price': 5990,
        'stock_quantity': 22,
        'description': 'Компактная портативная колонка с мощным басом и защитой от воды.',
        'specifications': {'Мощность': '5 Вт', 'Автономность': '16 часов', 'Защита': 'IP67'},
    },
    {
        'name': 'Xiaomi Powerbank 20000mAh',
        'slug': 'xiaomi-powerbank-20000',
        'category': 'accessories',
        'brand': 'xiaomi',
        'price': 2990,
        'stock_quantity': 35,
        'description': 'Внешний аккумулятор большой ёмкости с быстрой зарядкой 22.5 Вт.',
        'specifications': {'Ёмкость': '20000 мАч', 'Быстрая зарядка': '22.5 Вт', 'Портов': 2},
    },
]


class Command(BaseCommand):
    help = 'Наполняет каталог демо-товарами по существующим категориям и брендам'

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for item in PRODUCTS:
            try:
                category = Category.objects.get(slug=item['category'])
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"Пропущен '{item['name']}': категория '{item['category']}' не найдена"
                ))
                continue

            brand = None
            if item.get('brand'):
                try:
                    brand = Brand.objects.get(slug=item['brand'])
                except Brand.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"Бренд '{item['brand']}' не найден для '{item['name']}', оставляю пустым"
                    ))

            product, created = Product.objects.get_or_create(
                slug=item['slug'],
                defaults={
                    'name': item['name'],
                    'category': category,
                    'brand': brand,
                    'price': item['price'],
                    'stock_quantity': item['stock_quantity'],
                    'description': item['description'],
                    'specifications': item.get('specifications', {}),
                    'is_featured': item.get('is_featured', False),
                    'is_active': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Создан: {product.name}"))
            else:
                skipped_count += 1
                self.stdout.write(f"Уже существует: {product.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\nГотово! Создано новых товаров: {created_count}, пропущено (уже были): {skipped_count}"
        ))
