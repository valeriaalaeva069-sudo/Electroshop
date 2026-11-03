from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('guest', 'Гость'),
        ('customer', 'Покупатель'),
        ('admin', 'Администратор'),
    )

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    age = models.IntegerField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    def save(self, *args, **kwargs):
        # Админ магазина = полный админ. Админ-панель ведёт в Django-админку
        # (добавление товаров, пользователи), а туда пускает только is_staff/is_superuser.
        # Поэтому role='admin' и флаги держим согласованными в обе стороны.
        if self.role == 'admin' or self.is_superuser:
            self.role = 'admin'
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
