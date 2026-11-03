import re

from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models


class SiteSettings(models.Model):
    """Настройки сайта (единственная запись): название, иконка и контакты.

    Меняются в админке («Настройки сайта») без правки кода и шаблонов.
    """
    site_name = models.CharField('Название сайта', max_length=60, default='ElectroShop',
                                 help_text='Показывается в шапке, во вкладке браузера, в письмах и в админке')
    icon = models.FileField(
        'Иконка сайта (картинка)', upload_to='site/', blank=True,
        validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'svg', 'ico', 'webp'])],
        help_text='Квадратная картинка PNG, JPG, SVG, ICO или WEBP. Используется как логотип и как значок вкладки браузера',
    )
    fa_icon = models.CharField(
        'Иконка Font Awesome', max_length=40, default='fa-bolt',
        validators=[RegexValidator(r'^fa-[a-z0-9-]+$', 'Формат: fa-bolt, fa-microchip, fa-plug')],
        help_text='Используется, если картинка не загружена. Названия иконок: fontawesome.com/icons (например fa-bolt, fa-microchip)',
    )

    contact_phone = models.CharField('Телефон', max_length=30, blank=True, default='+7 (900) 000-00-00')
    contact_email = models.EmailField('Электронная почта', blank=True, default='support@electroshop.ru')
    contact_telegram = models.CharField('Telegram', max_length=60, blank=True, default='',
                                        help_text='Например @electroshop_support')
    contact_address = models.CharField('Адрес', max_length=200, blank=True, default='')
    working_hours = models.CharField('Часы работы поддержки', max_length=100, blank=True, default='Пн–Пт, 9:00–18:00')
    error_note = models.CharField(
        'Текст при ошибке сайта', max_length=200,
        default='Если сайт работает с ошибками, свяжитесь с нами:',
        help_text='Показывается в подвале, на страницах ошибок и во всплывающем сообщении при сбое сервера',
    )

    class Meta:
        verbose_name = 'настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return f'Настройки сайта «{self.site_name}»'

    def save(self, *args, **kwargs):
        self.pk = 1  # запись всегда одна
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # единственную запись удалить нельзя

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def phone_href(self):
        return re.sub(r'[^\d+]', '', self.contact_phone or '')

    @property
    def telegram_href(self):
        name = (self.contact_telegram or '').strip().lstrip('@')
        return f'https://t.me/{name}' if name else ''

    @property
    def has_contacts(self):
        return any([self.contact_phone, self.contact_email, self.contact_telegram, self.contact_address])
