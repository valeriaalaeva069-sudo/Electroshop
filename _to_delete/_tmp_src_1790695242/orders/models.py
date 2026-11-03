from django.db import models, transaction, IntegrityError
from django.conf import settings
from django.utils import timezone


class OrderStatus(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#gray')
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class Order(models.Model):
    DELIVERY_CHOICES = (
        ('pickup', 'Самовывоз'),
        ('courier', 'Курьер'),
        ('post', 'Почта'),
    )

    PAYMENT_CHOICES = (
        ('card', 'Карта онлайн'),
        ('cash', 'Наличные при получении'),
        ('card_delivery', 'Карта курьеру'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)

    status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT, related_name='orders')

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    city = models.CharField(max_length=100)
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)

    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default='courier')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='card')
    payment_status = models.BooleanField(default=False)

    tracking_number = models.CharField(max_length=100, blank=True)
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number}"

    def _next_number(self):
        today = timezone.now().strftime('%Y%m%d')
        last = Order.objects.filter(
            order_number__startswith=f"ORD-{today}"
        ).order_by('-order_number').first()
        num = int(last.order_number.split('-')[-1]) + 1 if last else 1
        return f"ORD-{today}-{num:04d}"

    def save(self, *args, **kwargs):
        if self.order_number:
            return super().save(*args, **kwargs)

        # Два запроса одновременно могут получить один номер — при коллизии пробуем снова
        for _ in range(5):
            self.order_number = self._next_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.order_number = ''
        raise IntegrityError('Не удалось сгенерировать уникальный номер заказа')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history_entries')
    status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT)
    comment = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['changed_at']