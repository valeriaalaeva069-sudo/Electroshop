import smtplib

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверка отправки почты: python manage.py test_email адрес@пример.ру'

    def add_arguments(self, parser):
        parser.add_argument('to', nargs='?', help='Куда отправить тестовое письмо (по умолчанию — на EMAIL_HOST_USER)')

    def handle(self, *args, to=None, **options):
        user = settings.EMAIL_HOST_USER
        pwd = settings.EMAIL_HOST_PASSWORD
        self.stdout.write(f'Сервер: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}, TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_HOST_USER: {user or "НЕ ЗАДАН"}')
        self.stdout.write(f'EMAIL_HOST_PASSWORD: {"задан, " + str(len(pwd)) + " символов" if pwd else "НЕ ЗАДАН"}')
        if not user or not pwd:
            self.stderr.write('Впиши EMAIL_HOST_USER и EMAIL_HOST_PASSWORD в файл .env и запусти команду снова.')
            return
        to = to or user
        try:
            send_mail('Проверка почты ElectroShop', 'Если вы читаете это письмо, отправка почты работает.',
                      settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
        except smtplib.SMTPAuthenticationError as e:
            self.stderr.write(f'Gmail отклонил логин или пароль: {e}\n'
                              'Нужен «пароль приложения» (16 символов), а не пароль от аккаунта; '
                              'двухфакторная защита Google должна быть включена.')
        except Exception as e:
            self.stderr.write(f'Не удалось отправить: {type(e).__name__}: {e}')
        else:
            self.stdout.write(self.style.SUCCESS(f'Письмо отправлено на {to}. Проверь входящие и папку «Спам».'))
