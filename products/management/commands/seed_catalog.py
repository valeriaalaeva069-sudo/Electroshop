from django.core.management.base import BaseCommand
from django.utils.text import slugify

from products.models import (
    Category, Brand, Product, Attribute, AttributeValue, ProductAttributeValue,
)

ALL_CATS = ['smartphones', 'laptops', 'accessories', 'audio', 'smartwatches',
            'mice', 'keyboards', 'headphones', 'cases']

# slug -> (название, категории, допустимые значения)
ATTRIBUTES = {
    'color': ('Цвет', ALL_CATS, ['Чёрный', 'Белый', 'Серебристый', 'Серый', 'Графитовый', 'Синий',
                                 'Фиолетовый', 'Красный', 'Розовый', 'Золотой', 'Жёлтый', 'Зелёный',
                                 'Бежевый', 'Коричневый', 'Прозрачный']),
    'ram': ('Оперативная память', ['smartphones', 'laptops'], ['4 ГБ', '8 ГБ', '12 ГБ', '16 ГБ', '32 ГБ']),
    'storage': ('Встроенная память', ['smartphones', 'laptops'], ['64 ГБ', '128 ГБ', '256 ГБ', '512 ГБ', '1 ТБ']),
    'screen': ('Диагональ экрана', ['smartphones', 'laptops', 'smartwatches'],
               ['1.4"', '1.5"', '1.8"', '1.96"', '6.1"', '6.2"', '6.4"', '6.6"', '6.7"', '6.8"',
                '13"', '14"', '15.6"', '16"']),
    'os': ('Операционная система', ['smartphones', 'laptops', 'smartwatches'],
           ['iOS', 'Android', 'macOS', 'Windows 11', 'Без ОС', 'watchOS', 'Wear OS', 'Собственная ОС']),
    'camera': ('Основная камера', ['smartphones'], ['12 Мп', '48 Мп', '50 Мп', '108 Мп', '200 Мп']),
    'battery': ('Аккумулятор', ['smartphones'], ['до 4000 мАч', '4000–5000 мАч', 'более 5000 мАч']),
    'cpu': ('Процессор', ['laptops'], ['Apple M2', 'Apple M3', 'Intel Core i5', 'Intel Core i7', 'AMD Ryzen 5', 'AMD Ryzen 7']),
    'laptop_type': ('Назначение', ['laptops'], ['Для учёбы и работы', 'Ультрабук', 'Игровой']),
    'watch_compat': ('Совместимость', ['smartwatches'], ['iOS', 'Android', 'iOS и Android']),
    'autonomy': ('Автономность', ['smartwatches'], ['до 2 дней', 'до 7 дней', '2 недели и более']),
    'water': ('Влагозащита', ['smartwatches', 'audio'], ['Есть', 'Нет']),
    'connection': ('Подключение', ['mice', 'keyboards', 'headphones', 'audio'],
                   ['Проводное', 'Bluetooth', 'Беспроводное 2.4 ГГц', 'Bluetooth + 2.4 ГГц']),
    'mouse_type': ('Тип мыши', ['mice'], ['Офисная', 'Игровая', 'Эргономичная']),
    'switch': ('Тип клавиш', ['keyboards'], ['Механическая', 'Мембранная', 'Ножничная']),
    'kb_format': ('Формат', ['keyboards'], ['Полноразмерная', 'Компактная (TKL)', 'Компактная (75%)']),
    'headphone_type': ('Тип наушников', ['headphones'], ['Вкладыши', 'Накладные', 'Полноразмерные', 'Спортивные']),
    'anc': ('Шумоподавление', ['headphones'], ['Есть', 'Нет']),
    'speaker_type': ('Тип', ['audio'], ['Портативная колонка', 'Умная колонка', 'Саундбар']),
    'power': ('Мощность', ['audio'], ['до 10 Вт', '10–30 Вт', 'более 30 Вт']),
    'case_compat': ('Совместимость', ['cases'], ['iPhone 15', 'iPhone 15 Pro', 'Galaxy S24', 'Redmi Note 13', 'Универсальный']),
    'case_material': ('Материал', ['cases'], ['Силикон', 'Пластик', 'Экокожа', 'TPU']),
    'acc_type': ('Тип аксессуара', ['accessories'],
                 ['Внешний аккумулятор', 'Зарядное устройство', 'Кабель', 'Адаптер и хаб', 'Держатель']),
}

NEW_BRANDS = {
    'lenovo': 'Lenovo', 'asus': 'ASUS', 'hp': 'HP', 'huawei': 'Huawei', 'honor': 'Honor',
    'google': 'Google', 'nothing': 'Nothing', 'jbl': 'JBL', 'anker': 'Anker', 'razer': 'Razer',
    'garmin': 'Garmin', 'marshall': 'Marshall', 'baseus': 'Baseus', 'keychron': 'Keychron',
    'hyperx': 'HyperX', 'redragon': 'Redragon', 'amazfit': 'Amazfit', 'ugreen': 'UGREEN',
    'bose': 'Bose', 'sennheiser': 'Sennheiser', 'edifier': 'Edifier', 'jabra': 'Jabra',
}

# Значения фильтров для уже существующих демо-товаров
EXISTING = {
    'iphone-15-pro-128gb': dict(ram='8 ГБ', screen='6.1"', os='iOS', camera='48 Мп', battery='до 4000 мАч'),
    'samsung-galaxy-s24': dict(ram='8 ГБ', screen='6.2"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    'xiaomi-redmi-note-13': dict(ram='8 ГБ', screen='6.7"', os='Android', camera='108 Мп', battery='4000–5000 мАч'),
    'macbook-air-13-m2': dict(screen='13"', os='macOS', cpu='Apple M2', laptop_type='Ультрабук'),
    'samsung-galaxy-book4': dict(screen='15.6"', os='Windows 11', cpu='Intel Core i5', laptop_type='Для учёбы и работы'),
    'sony-wh-1000xm5': dict(headphone_type='Полноразмерные', connection='Bluetooth', anc='Есть'),
    'apple-airpods-pro-2': dict(headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    'logitech-mx-master-3s': dict(mouse_type='Эргономичная', connection='Bluetooth + 2.4 ГГц'),
    'logitech-mx-keys': dict(switch='Ножничная', kb_format='Полноразмерная', connection='Bluetooth + 2.4 ГГц'),
    'apple-watch-series-9': dict(screen='1.8"', os='watchOS', watch_compat='iOS', autonomy='до 2 дней', water='Есть'),
    'xiaomi-smart-band-8': dict(screen='1.4"', os='Собственная ОС', watch_compat='iOS и Android',
                                autonomy='2 недели и более', water='Есть'),
    'apple-silicone-case-iphone-15': dict(case_compat='iPhone 15', case_material='Силикон'),
    'sony-srs-xb13': dict(speaker_type='Портативная колонка', power='до 10 Вт', connection='Bluetooth', water='Есть'),
    'xiaomi-powerbank-20000': dict(acc_type='Внешний аккумулятор'),
}


def P(cat, brand, name, price, stock, desc, specs, featured=False, **attrs):
    return dict(cat=cat, brand=brand, name=name, price=price, stock=stock, desc=desc,
                specs=specs, featured=featured, attrs=attrs)


PRODUCTS = [
    # ---- Смартфоны
    P('smartphones', 'google', 'Google Pixel 8 128GB', 62990, 9,
      'Смартфон Google с чистым Android и сильной камерой.',
      {'Процессор': 'Google Tensor G3', 'Экран': '6.2" OLED', 'Камера': '50 Мп'}, True,
      color='Чёрный', ram='8 ГБ', storage='128 ГБ', screen='6.2"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'honor', 'Honor 200 256GB', 39990, 14,
      'Смартфон с портретной камерой и быстрой зарядкой 100 Вт.',
      {'Экран': '6.7" AMOLED', 'Зарядка': '100 Вт', 'Камера': '50 Мп'},
      color='Зелёный', ram='12 ГБ', storage='256 ГБ', screen='6.7"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'samsung', 'Samsung Galaxy A55 128GB', 36990, 22,
      'Среднебюджетный смартфон с металлической рамкой и защитой от воды.',
      {'Экран': '6.6" Super AMOLED', 'Защита': 'IP67', 'Камера': '50 Мп'},
      color='Синий', ram='8 ГБ', storage='128 ГБ', screen='6.6"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'apple', 'iPhone 15 128GB', 79990, 18,
      'iPhone 15 с Dynamic Island и USB-C.',
      {'Процессор': 'A16 Bionic', 'Экран': '6.1" OLED', 'Камера': '48 Мп'}, True,
      color='Розовый', ram='8 ГБ', storage='128 ГБ', screen='6.1"', os='iOS', camera='48 Мп', battery='до 4000 мАч'),
    P('smartphones', 'xiaomi', 'Xiaomi 14T 256GB', 54990, 11,
      'Смартфон с камерой Leica и экраном 144 Гц.',
      {'Экран': '6.7" AMOLED 144 Гц', 'Зарядка': '67 Вт', 'Камера': '50 Мп'},
      color='Серый', ram='12 ГБ', storage='256 ГБ', screen='6.7"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'nothing', 'Nothing Phone (2a) 256GB', 27990, 16,
      'Смартфон с прозрачной задней панелью и подсветкой Glyph.',
      {'Экран': '6.7" AMOLED', 'Зарядка': '45 Вт'},
      color='Белый', ram='12 ГБ', storage='256 ГБ', screen='6.7"', os='Android', camera='50 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'samsung', 'Samsung Galaxy S24 Ultra 512GB', 119990, 6,
      'Флагман с S Pen, титановым корпусом и камерой 200 Мп.',
      {'Экран': '6.8" AMOLED', 'Камера': '200 Мп', 'Перо': 'S Pen'}, True,
      color='Серебристый', ram='12 ГБ', storage='512 ГБ', screen='6.8"', os='Android', camera='200 Мп', battery='4000–5000 мАч'),
    P('smartphones', 'xiaomi', 'Redmi 13C 128GB', 10990, 40,
      'Недорогой смартфон для повседневных задач.',
      {'Экран': '6.74" IPS', 'Зарядка': '18 Вт'},
      color='Чёрный', ram='4 ГБ', storage='128 ГБ', screen='6.7"', os='Android', camera='50 Мп', battery='более 5000 мАч'),

    # ---- Ноутбуки
    P('laptops', 'apple', 'MacBook Air 15" M3 256GB', 139990, 5,
      'Тонкий ноутбук с большим экраном и чипом Apple M3.',
      {'Процессор': 'Apple M3', 'Экран': '15.3" Retina'}, True,
      color='Серый', ram='8 ГБ', storage='256 ГБ', screen='15.6"', os='macOS', cpu='Apple M3', laptop_type='Ультрабук'),
    P('laptops', 'lenovo', 'Lenovo IdeaPad Slim 3 15', 54990, 12,
      'Ноутбук для учёбы и офисной работы.',
      {'Процессор': 'AMD Ryzen 5 7530U', 'Экран': '15.6" IPS', 'SSD': '512 ГБ'},
      color='Серый', ram='16 ГБ', storage='512 ГБ', screen='15.6"', os='Без ОС', cpu='AMD Ryzen 5', laptop_type='Для учёбы и работы'),
    P('laptops', 'asus', 'ASUS Vivobook 14', 47990, 15,
      'Лёгкий ноутбук с металлической крышкой.',
      {'Процессор': 'Intel Core i5-1235U', 'Экран': '14" IPS'},
      color='Серебристый', ram='8 ГБ', storage='512 ГБ', screen='14"', os='Windows 11', cpu='Intel Core i5', laptop_type='Для учёбы и работы'),
    P('laptops', 'asus', 'ASUS TUF Gaming F15', 89990, 7,
      'Игровой ноутбук с дискретной видеокартой и экраном 144 Гц.',
      {'Процессор': 'Intel Core i7-12700H', 'Видеокарта': 'GeForce RTX 4050', 'Экран': '15.6" 144 Гц'},
      color='Чёрный', ram='16 ГБ', storage='512 ГБ', screen='15.6"', os='Без ОС', cpu='Intel Core i7', laptop_type='Игровой'),
    P('laptops', 'hp', 'HP Pavilion 16', 71990, 8,
      'Ноутбук с большим экраном для работы и мультимедиа.',
      {'Процессор': 'AMD Ryzen 7 7730U', 'Экран': '16" IPS'},
      color='Серебристый', ram='16 ГБ', storage='1 ТБ', screen='16"', os='Windows 11', cpu='AMD Ryzen 7', laptop_type='Для учёбы и работы'),
    P('laptops', 'huawei', 'Huawei MateBook D 14', 52990, 10,
      'Компактный ноутбук с металлическим корпусом.',
      {'Процессор': 'Intel Core i5-12450H', 'Экран': '14" IPS'},
      color='Серый', ram='16 ГБ', storage='512 ГБ', screen='14"', os='Без ОС', cpu='Intel Core i5', laptop_type='Ультрабук'),
    P('laptops', 'lenovo', 'Lenovo Legion 5', 109990, 4,
      'Игровой ноутбук с мощной графикой и хорошим охлаждением.',
      {'Процессор': 'AMD Ryzen 7 7735HS', 'Видеокарта': 'GeForce RTX 4060', 'Экран': '15.6" 165 Гц'},
      color='Серый', ram='32 ГБ', storage='1 ТБ', screen='15.6"', os='Без ОС', cpu='AMD Ryzen 7', laptop_type='Игровой'),
    P('laptops', 'apple', 'MacBook Pro 14" M3 512GB', 179990, 3,
      'Профессиональный ноутбук с экраном mini-LED.',
      {'Процессор': 'Apple M3', 'Экран': '14.2" Liquid Retina XDR'},
      color='Серебристый', ram='16 ГБ', storage='512 ГБ', screen='14"', os='macOS', cpu='Apple M3', laptop_type='Ультрабук'),

    # ---- Умные часы
    P('smartwatches', 'samsung', 'Samsung Galaxy Watch6 44mm', 22990, 13,
      'Умные часы с мониторингом сна и ЭКГ.',
      {'Экран': '1.5" AMOLED', 'Датчики': 'ЭКГ, пульс, SpO2'},
      color='Серебристый', screen='1.5"', os='Wear OS', watch_compat='Android', autonomy='до 2 дней', water='Есть'),
    P('smartwatches', 'huawei', 'Huawei Watch GT 4 46mm', 19990, 17,
      'Часы с длительной автономностью и режимами тренировок.',
      {'Экран': '1.43" AMOLED', 'Автономность': 'до 14 дней'},
      color='Чёрный', screen='1.4"', os='Собственная ОС', watch_compat='iOS и Android', autonomy='2 недели и более', water='Есть'),
    P('smartwatches', 'amazfit', 'Amazfit Bip 5', 7990, 26,
      'Недорогие часы с большим экраном и GPS.',
      {'Экран': '1.91" TFT', 'GPS': 'Да'},
      color='Чёрный', screen='1.96"', os='Собственная ОС', watch_compat='iOS и Android', autonomy='2 недели и более', water='Есть'),
    P('smartwatches', 'garmin', 'Garmin Forerunner 265', 41990, 6,
      'Беговые часы с AMOLED-экраном и метриками восстановления.',
      {'Экран': '1.3" AMOLED', 'GPS': 'Мультидиапазонный'},
      color='Синий', screen='1.4"', os='Собственная ОС', watch_compat='iOS и Android', autonomy='до 7 дней', water='Есть'),
    P('smartwatches', 'apple', 'Apple Watch SE 2 44mm', 27990, 14,
      'Базовые часы Apple с датчиком падения и мониторингом пульса.',
      {'Экран': '1.78" OLED', 'Процессор': 'S8'},
      color='Белый', screen='1.8"', os='watchOS', watch_compat='iOS', autonomy='до 2 дней', water='Есть'),
    P('smartwatches', 'xiaomi', 'Xiaomi Watch S3', 11990, 21,
      'Часы со сменными безелями и AMOLED-экраном.',
      {'Экран': '1.43" AMOLED', 'Автономность': 'до 15 дней'},
      color='Серебристый', screen='1.4"', os='Собственная ОС', watch_compat='iOS и Android', autonomy='2 недели и более', water='Есть'),

    # ---- Мышки
    P('mice', 'logitech', 'Logitech G502 Hero', 4990, 30, 'Игровая мышь с сенсором Hero 25K.',
      {'Разрешение': 'до 25600 DPI', 'Кнопки': '11'},
      color='Чёрный', connection='Проводное', mouse_type='Игровая'),
    P('mice', 'logitech', 'Logitech M331 Silent', 1990, 45, 'Беспроводная мышь с тихими кликами для офиса.',
      {'Разрешение': '1000 DPI'},
      color='Чёрный', connection='Беспроводное 2.4 ГГц', mouse_type='Офисная'),
    P('mice', 'razer', 'Razer DeathAdder V3', 6990, 12, 'Лёгкая игровая мышь для шутеров.',
      {'Разрешение': 'до 30000 DPI', 'Вес': '59 г'},
      color='Чёрный', connection='Проводное', mouse_type='Игровая'),
    P('mice', 'xiaomi', 'Xiaomi Wireless Mouse Lite 2', 890, 60, 'Простая беспроводная мышь.',
      {'Разрешение': '1000 DPI'},
      color='Серый', connection='Беспроводное 2.4 ГГц', mouse_type='Офисная'),
    P('mice', 'logitech', 'Logitech MX Vertical', 8990, 9, 'Вертикальная мышь для работы без нагрузки на запястье.',
      {'Разрешение': 'до 4000 DPI'},
      color='Чёрный', connection='Bluetooth + 2.4 ГГц', mouse_type='Эргономичная'),
    P('mice', 'apple', 'Apple Magic Mouse', 9990, 8, 'Мышь с сенсорной поверхностью для жестов.',
      {'Подключение': 'Bluetooth'},
      color='Белый', connection='Bluetooth', mouse_type='Офисная'),
    P('mice', 'redragon', 'Redragon Cobra M711', 1690, 34, 'Недорогая игровая мышь с подсветкой.',
      {'Разрешение': 'до 10000 DPI', 'Кнопки': '7'},
      color='Чёрный', connection='Проводное', mouse_type='Игровая'),

    # ---- Клавиатуры
    P('keyboards', 'keychron', 'Keychron K2 V2', 8990, 10, 'Компактная механическая клавиатура 75%.',
      {'Переключатели': 'Gateron Brown', 'Раскладка': '84 клавиши'},
      color='Серый', connection='Bluetooth + 2.4 ГГц', switch='Механическая', kb_format='Компактная (75%)'),
    P('keyboards', 'logitech', 'Logitech K380', 3490, 28, 'Тонкая многоустройственная клавиатура.',
      {'Подключение': 'Bluetooth до 3 устройств'},
      color='Розовый', connection='Bluetooth', switch='Мембранная', kb_format='Компактная (TKL)'),
    P('keyboards', 'hyperx', 'HyperX Alloy Origins 60', 8490, 9, 'Игровая клавиатура 60% с алюминиевым корпусом.',
      {'Переключатели': 'HyperX Red'},
      color='Чёрный', connection='Проводное', switch='Механическая', kb_format='Компактная (75%)'),
    P('keyboards', 'redragon', 'Redragon Kumara K552', 3290, 25, 'Механическая клавиатура TKL с подсветкой.',
      {'Переключатели': 'Outemu Blue'},
      color='Чёрный', connection='Проводное', switch='Механическая', kb_format='Компактная (TKL)'),
    P('keyboards', 'apple', 'Apple Magic Keyboard', 12990, 7, 'Тонкая клавиатура с ножничным механизмом.',
      {'Подключение': 'Bluetooth', 'Раскладка': 'Русская'},
      color='Белый', connection='Bluetooth', switch='Ножничная', kb_format='Полноразмерная'),
    P('keyboards', 'razer', 'Razer BlackWidow V4 X', 12990, 6, 'Полноразмерная механическая клавиатура с макро-клавишами.',
      {'Переключатели': 'Razer Green'},
      color='Чёрный', connection='Проводное', switch='Механическая', kb_format='Полноразмерная'),

    # ---- Наушники
    P('headphones', 'sony', 'Sony WF-1000XM5', 24990, 15, 'Вкладыши с шумоподавлением и Hi-Res звуком.',
      {'Автономность': '8 часов', 'Шумоподавление': 'Да'},
      color='Чёрный', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    P('headphones', 'samsung', 'Samsung Galaxy Buds2 Pro', 14990, 20, 'Компактные вкладыши с шумоподавлением.',
      {'Автономность': '5 часов', 'Шумоподавление': 'Да'},
      color='Серый', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    P('headphones', 'jbl', 'JBL Tune 520BT', 3990, 35, 'Накладные наушники с басовым звучанием.',
      {'Автономность': '57 часов'},
      color='Синий', headphone_type='Накладные', connection='Bluetooth', anc='Нет'),
    P('headphones', 'hyperx', 'HyperX Cloud II', 8990, 12, 'Игровая гарнитура с виртуальным звуком 7.1.',
      {'Микрофон': 'Съёмный'},
      color='Красный', headphone_type='Полноразмерные', connection='Проводное', anc='Нет'),
    P('headphones', 'apple', 'Apple AirPods Max', 54990, 4, 'Полноразмерные наушники с активным шумоподавлением.',
      {'Автономность': '20 часов'},
      color='Серебристый', headphone_type='Полноразмерные', connection='Bluetooth', anc='Есть'),
    P('headphones', 'xiaomi', 'Redmi Buds 5', 2990, 42, 'Недорогие вкладыши с шумоподавлением.',
      {'Автономность': '10 часов'},
      color='Чёрный', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    P('headphones', 'jbl', 'JBL Endurance Peak 3', 5990, 18, 'Спортивные вкладыши с защитой от воды.',
      {'Автономность': '10 часов', 'Защита': 'IP68'},
      color='Зелёный', headphone_type='Спортивные', connection='Bluetooth', anc='Нет'),

    P('headphones', 'bose', 'Bose QuietComfort Ultra', 39990, 8, 'Полноразмерные наушники с лучшим шумоподавлением в классе.',
      {'Автономность': '24 часа'}, True,
      color='Чёрный', headphone_type='Полноразмерные', connection='Bluetooth', anc='Есть'),
    P('headphones', 'sennheiser', 'Sennheiser Momentum 4', 29990, 10, 'Накладные наушники с отличным звуком и автономностью.',
      {'Автономность': '60 часов'},
      color='Белый', headphone_type='Накладные', connection='Bluetooth', anc='Есть'),
    P('headphones', 'apple', 'Apple AirPods 4', 14990, 28, 'Вкладыши с пространственным звуком.',
      {'Автономность': '5 часов'},
      color='Белый', headphone_type='Вкладыши', connection='Bluetooth', anc='Нет'),
    P('headphones', 'sony', 'Sony WH-CH520', 4990, 30, 'Лёгкие накладные наушники на каждый день.',
      {'Автономность': '50 часов'},
      color='Чёрный', headphone_type='Накладные', connection='Bluetooth', anc='Нет'),
    P('headphones', 'razer', 'Razer BlackShark V2 X', 5990, 14, 'Игровая гарнитура с кардиоидным микрофоном.',
      {'Микрофон': 'Съёмный'},
      color='Чёрный', headphone_type='Полноразмерные', connection='Проводное', anc='Нет'),
    P('headphones', 'nothing', 'Nothing Ear (a)', 7990, 19, 'Прозрачные вкладыши с шумоподавлением.',
      {'Автономность': '9.5 часов'},
      color='Жёлтый', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    P('headphones', 'huawei', 'Huawei FreeBuds Pro 3', 15990, 11, 'Вкладыши с адаптивным шумоподавлением.',
      {'Автономность': '6.5 часов'},
      color='Серебристый', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),
    P('headphones', 'jabra', 'Jabra Elite 8 Active', 17990, 9, 'Спортивные вкладыши с защитой IP68.',
      {'Автономность': '8 часов', 'Защита': 'IP68'},
      color='Чёрный', headphone_type='Спортивные', connection='Bluetooth', anc='Есть'),
    P('headphones', 'xiaomi', 'Xiaomi Redmi Buds 4 Active', 1490, 60, 'Бюджетные вкладыши для повседневного использования.',
      {'Автономность': '12 часов'},
      color='Чёрный', headphone_type='Вкладыши', connection='Bluetooth', anc='Нет'),
    P('headphones', 'sennheiser', 'Sennheiser HD 560S', 14990, 7, 'Проводные мониторные наушники для музыки.',
      {'Импеданс': '120 Ом'},
      color='Чёрный', headphone_type='Полноразмерные', connection='Проводное', anc='Нет'),
    P('headphones', 'samsung', 'Samsung Galaxy Buds FE', 6990, 24, 'Вкладыши с шумоподавлением по доступной цене.',
      {'Автономность': '6 часов'},
      color='Графитовый', headphone_type='Вкладыши', connection='Bluetooth', anc='Есть'),

    # ---- Аудио
    P('audio', 'jbl', 'JBL Flip 6', 9990, 24, 'Портативная колонка с защитой IP67.',
      {'Мощность': '30 Вт', 'Автономность': '12 часов'}, True,
      color='Синий', speaker_type='Портативная колонка', power='10–30 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'marshall', 'Marshall Emberton II', 15990, 9, 'Компактная колонка с фирменным звучанием.',
      {'Мощность': '20 Вт', 'Автономность': '30 часов'},
      color='Чёрный', speaker_type='Портативная колонка', power='10–30 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'sony', 'Sony HT-S400 Soundbar', 24990, 6, 'Саундбар 2.1 с беспроводным сабвуфером.',
      {'Мощность': '330 Вт', 'Каналы': '2.1'},
      color='Чёрный', speaker_type='Саундбар', power='более 30 Вт', connection='Bluetooth', water='Нет'),
    P('audio', 'xiaomi', 'Xiaomi Smart Speaker', 5990, 15, 'Умная колонка с голосовым помощником.',
      {'Мощность': '12 Вт'},
      color='Белый', speaker_type='Умная колонка', power='10–30 Вт', connection='Bluetooth', water='Нет'),
    P('audio', 'jbl', 'JBL Go 4', 3490, 50, 'Маленькая колонка для прогулок.',
      {'Мощность': '4.2 Вт', 'Автономность': '7 часов'},
      color='Красный', speaker_type='Портативная колонка', power='до 10 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'samsung', 'Samsung HW-B550 Soundbar', 21990, 5, 'Саундбар 2.1 с Dolby Digital.',
      {'Мощность': '410 Вт', 'Каналы': '2.1'},
      color='Чёрный', speaker_type='Саундбар', power='более 30 Вт', connection='Bluetooth', water='Нет'),

    P('audio', 'bose', 'Bose SoundLink Flex', 14990, 13, 'Портативная колонка с защитой от воды и пыли.',
      {'Мощность': '20 Вт', 'Автономность': '12 часов'},
      color='Чёрный', speaker_type='Портативная колонка', power='10–30 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'edifier', 'Edifier R1280DB', 12990, 10, 'Активные полочные колонки с Bluetooth.',
      {'Мощность': '42 Вт'},
      color='Коричневый', speaker_type='Умная колонка', power='более 30 Вт', connection='Bluetooth', water='Нет'),
    P('audio', 'jbl', 'JBL Charge 5', 14990, 16, 'Мощная колонка с функцией внешнего аккумулятора.',
      {'Мощность': '40 Вт', 'Автономность': '20 часов'},
      color='Синий', speaker_type='Портативная колонка', power='более 30 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'jbl', 'JBL Bar 500', 44990, 4, 'Саундбар 5.1 с беспроводным сабвуфером.',
      {'Мощность': '590 Вт', 'Каналы': '5.1'},
      color='Чёрный', speaker_type='Саундбар', power='более 30 Вт', connection='Bluetooth', water='Нет'),
    P('audio', 'sony', 'Sony SRS-XB100', 4490, 35, 'Компактная колонка с карабином.',
      {'Мощность': '8 Вт', 'Автономность': '16 часов'},
      color='Синий', speaker_type='Портативная колонка', power='до 10 Вт', connection='Bluetooth', water='Есть'),
    P('audio', 'marshall', 'Marshall Stanmore III', 34990, 5, 'Домашняя колонка в стиле гитарного усилителя.',
      {'Мощность': '80 Вт'},
      color='Чёрный', speaker_type='Умная колонка', power='более 30 Вт', connection='Bluetooth', water='Нет'),

    # ---- Аксессуары
    P('accessories', 'anker', 'Anker 737 Power Bank 24000', 11990, 12,
      'Мощный внешний аккумулятор с быстрой зарядкой 140 Вт.',
      {'Ёмкость': '24000 мА·ч', 'Мощность': '140 Вт'}, color='Чёрный', acc_type='Внешний аккумулятор'),
    P('accessories', 'baseus', 'Baseus GaN5 Pro 65W', 3490, 30, 'Компактное зарядное устройство на три порта.',
      {'Мощность': '65 Вт', 'Порты': '2×USB-C, USB-A'}, color='Белый', acc_type='Зарядное устройство'),
    P('accessories', 'ugreen', 'UGREEN USB-C кабель 100W 2 м', 990, 80,
      'Кабель для быстрой зарядки ноутбуков и телефонов.',
      {'Длина': '2 м', 'Мощность': '100 Вт'}, color='Чёрный', acc_type='Кабель'),
    P('accessories', 'apple', 'Apple 20W USB-C Power Adapter', 1990, 40, 'Оригинальный адаптер питания Apple.',
      {'Мощность': '20 Вт'}, color='Белый', acc_type='Зарядное устройство'),
    P('accessories', 'ugreen', 'UGREEN USB-C Hub 6-in-1', 4490, 20,
      'Хаб с HDMI, USB-A и слотом для карт памяти.',
      {'Порты': 'HDMI, 3×USB-A, SD, USB-C PD'}, color='Серый', acc_type='Адаптер и хаб'),
    P('accessories', 'baseus', 'Baseus магнитный держатель для авто', 1290, 45,
      'Держатель для смартфона на вентиляционную решётку.',
      {'Крепление': 'Магнитное'}, color='Чёрный', acc_type='Держатель'),
    P('accessories', 'anker', 'Anker PowerCore 10000', 2990, 33, 'Компактный внешний аккумулятор.',
      {'Ёмкость': '10000 мА·ч'}, color='Синий', acc_type='Внешний аккумулятор'),
    P('accessories', 'apple', 'Apple MagSafe Charger', 4990, 18, 'Беспроводная зарядка для iPhone.',
      {'Мощность': '15 Вт'}, color='Белый', acc_type='Зарядное устройство'),

    # ---- Чехлы
    P('cases', 'apple', 'Apple Silicone Case iPhone 15 Pro', 5990, 25, 'Силиконовый чехол с MagSafe.',
      {'Крепление': 'MagSafe'}, color='Синий', case_compat='iPhone 15 Pro', case_material='Силикон'),
    P('cases', 'samsung', 'Samsung Silicone Cover Galaxy S24', 2490, 30, 'Тонкий силиконовый чехол.',
      {'Толщина': '1.2 мм'}, color='Фиолетовый', case_compat='Galaxy S24', case_material='Силикон'),
    P('cases', 'xiaomi', 'Redmi Note 13 Clear Case', 490, 90, 'Прозрачный чехол из TPU.',
      {'Защита': 'Углы усилены'}, color='Прозрачный', case_compat='Redmi Note 13', case_material='TPU'),
    P('cases', 'baseus', 'Baseus Crystal Case iPhone 15', 1290, 40, 'Прозрачный чехол, не желтеет со временем.',
      {'Защита': 'Усиленные углы'}, color='Прозрачный', case_compat='iPhone 15', case_material='TPU'),
    P('cases', 'apple', 'Apple Leather Wallet iPhone 15', 6990, 10, 'Кошелёк из экокожи с MagSafe.',
      {'Карманы': '3 карты'}, color='Бежевый', case_compat='iPhone 15', case_material='Экокожа'),
    P('cases', 'ugreen', 'UGREEN Universal Phone Case', 590, 70, 'Универсальный пластиковый чехол.',
      {'Размер': 'до 6.7"'}, color='Чёрный', case_compat='Универсальный', case_material='Пластик'),
    P('cases', 'samsung', 'Samsung Smart View Wallet Galaxy S24', 3990, 14, 'Чехол-книжка с окном.',
      {'Окно': 'Да'}, color='Чёрный', case_compat='Galaxy S24', case_material='Экокожа'),
]


class Command(BaseCommand):
    help = 'Добавляет бренды, фильтры и демо-товары во все категории (можно запускать повторно)'

    def handle(self, *args, **options):
        audio = Category.objects.filter(slug='audio').first()
        if audio:
            Category.objects.filter(slug='headphones').update(parent=audio)

        for slug, name in NEW_BRANDS.items():
            Brand.objects.get_or_create(slug=slug, defaults={'name': name})

        attrs, values = {}, {}
        for order, (slug, (name, cats, vals)) in enumerate(ATTRIBUTES.items()):
            attr, _ = Attribute.objects.get_or_create(slug=slug, defaults={'name': name})
            attr.name = name
            attr.order = order
            attr.save()
            attr.categories.add(*Category.objects.filter(slug__in=cats))
            attrs[slug] = attr
            values[slug] = {}
            for i, v in enumerate(vals):
                obj, _ = AttributeValue.objects.get_or_create(attribute=attr, value=v)
                if obj.order != i:
                    obj.order = i
                    obj.save()
                values[slug][v] = obj

        def set_attr(product, slug, val):
            obj = values[slug].get(val)
            if obj is None:
                # значения нет в списке ATTRIBUTES — ставим его в конец, а не первым (order=0)
                obj, _ = AttributeValue.objects.get_or_create(
                    attribute=attrs[slug], value=val, defaults={'order': len(values[slug])})
                values[slug][val] = obj
            ProductAttributeValue.objects.update_or_create(
                product=product, attribute=attrs[slug], defaults={'value': obj})

        created = 0
        for item in PRODUCTS:
            category = Category.objects.get(slug=item['cat'])
            brand = Brand.objects.get(slug=item['brand'])
            slug = slugify(item['name']) or slugify(item['brand'] + '-' + str(item['price']))
            product, was_created = Product.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=item['name'], category=category, brand=brand, price=item['price'],
                    stock_quantity=item['stock'], description=item['desc'],
                    specifications=item['specs'], is_featured=item['featured'], is_active=True),
            )
            created += was_created
            for a, v in item['attrs'].items():
                set_attr(product, a, v)

        for slug, data in EXISTING.items():
            product = Product.objects.filter(slug=slug).first()
            if not product:
                continue
            for a, v in data.items():
                set_attr(product, a, v)

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Новых товаров: {created}, всего товаров: {Product.objects.count()}, '
            f'фильтров: {Attribute.objects.count()}'))