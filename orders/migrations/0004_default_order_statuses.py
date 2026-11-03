import re

from django.db import migrations

# Статусы, без которых магазин не работает: «Оформлен» нужен при создании заказа,
# «Оплачен» — при оплате, «Отменён» — для отмены, остальные — для отслеживания.
DEFAULT_STATUSES = [
    ('Оформлен', '#6c757d', 1),
    ('Оплачен', '#0088ff', 2),
    ('В сборке', '#8e44ad', 3),
    ('Собран', '#ff9900', 4),
    ('В пути', '#00aaff', 5),
    ('Доставлен', '#00cc66', 6),
    ('Получен', '#006633', 7),
    ('Отменён', '#ff0000', 8),
]

HEX_COLOR = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


def create_statuses(apps, schema_editor):
    OrderStatus = apps.get_model('orders', 'OrderStatus')
    for name, color, order in DEFAULT_STATUSES:
        status, created = OrderStatus.objects.get_or_create(
            name=name, defaults={'color': color, 'order': order}
        )
        # Уже существующие статусы не трогаем, кроме битого цвета вроде "#gray"
        if not created and not HEX_COLOR.match(status.color or ''):
            status.color = color
            status.save(update_fields=['color'])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_orderstatus_color_default'),
    ]

    operations = [
        migrations.RunPython(create_statuses, migrations.RunPython.noop),
    ]
