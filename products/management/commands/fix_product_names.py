from django.core.management.base import BaseCommand
from products.models import Product


class Command(BaseCommand):
    help = 'Убирает "опасные" двойные кавычки из названий товаров (ломают onclick в вёрстке)'

    def handle(self, *args, **options):
        fixes = {
            'macbook-air-13-m2': 'MacBook Air 13-inch M2',
        }

        for slug, new_name in fixes.items():
            updated = Product.objects.filter(slug=slug).update(name=new_name)
            if updated:
                self.stdout.write(self.style.SUCCESS(f"Переименован '{slug}' -> '{new_name}'"))
            else:
                self.stdout.write(self.style.WARNING(f"Товар со slug '{slug}' не найден"))
