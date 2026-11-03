from django.contrib import admin, messages
from .models import (
    Order, OrderItem, OrderStatus, OrderStatusHistory,
    CANCELLED_STATUS, return_items_to_stock,
)

# Регистрируем статусы заказов
@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'order', 'is_active']
    list_editable = ['order']
    ordering = ['order']

# Регистрируем заказы
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__email']
    readonly_fields = ['order_number', 'created_at']

    def save_model(self, request, obj, form, change):
        # Смена статуса через Django-админку подчиняется тем же правилам, что и через API:
        # отмена возвращает товар на склад, отменённый заказ «воскресить» нельзя
        if change and 'status' in form.changed_data:
            old_status = Order.objects.select_related('status').get(pk=obj.pk).status
            if old_status.name == CANCELLED_STATUS and obj.status.name != CANCELLED_STATUS:
                obj.status = old_status
                messages.error(request, 'Заказ отменён: товар уже вернулся на склад, статус не изменён')
            else:
                if obj.status.name == CANCELLED_STATUS and old_status.name != CANCELLED_STATUS:
                    return_items_to_stock(obj)
                OrderStatusHistory.objects.create(
                    order=obj, status=obj.status,
                    comment='Изменено в Django-админке', changed_by=request.user,
                )
        super().save_model(request, obj, form, change)

# Регистрируем позиции заказов
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'price', 'quantity']

# Регистрируем историю статусов
@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'changed_at']
    readonly_fields = ['changed_at']