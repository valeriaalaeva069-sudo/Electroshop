from django.db import models
from django.conf import settings
from orders.models import Order


class Payment(models.Model):
    """Модель платежа"""
    STATUS_CHOICES = (
        ('pending', 'Ожидает оплаты'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменён'),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='card')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'платёж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f"Payment for {self.order.order_number}"