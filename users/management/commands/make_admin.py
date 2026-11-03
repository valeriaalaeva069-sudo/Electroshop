from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Выдаёт полные права администратора указанному пользователю по email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email пользователя, которому выдать права админа')

    def handle(self, *args, **options):
        email = options['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь с email {email} не найден'))
            return

        # role='admin' — админ магазина (админ-панель и API, см. users.permissions.is_shop_admin)
        # is_staff/is_superuser — вход в Django-админку (/admin/).
        # CustomUser.save() и так проставит флаги по роли, здесь для наглядности.
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f'Готово! {user.email} теперь полноправный администратор '
            f'(role=admin, is_staff=True, is_superuser=True).'
        ))
