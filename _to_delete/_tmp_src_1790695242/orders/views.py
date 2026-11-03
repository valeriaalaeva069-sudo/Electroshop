from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.db import transaction
from products.models import Product
from django.shortcuts import get_object_or_404

from notifications.utils import send_order_update, send_notification_to_user
from users.permissions import IsAdminRole
from .emails import send_order_confirmation_email
from .models import Order, OrderItem, OrderStatus, OrderStatusHistory
from .serializers import (
    OrderSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderStatusSerializer,
)
from cart.models import Cart


class OrderListView(generics.ListAPIView):
    """Список заказов пользователя (админ видит все)"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.role == 'admin':
            return Order.objects.select_related('status', 'user').prefetch_related('items', 'status_history_entries__status', 'status_history_entries__changed_by')
        return Order.objects.select_related('status', 'user').prefetch_related('items', 'status_history_entries__status', 'status_history_entries__changed_by').filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    """Детали заказа"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.role == 'admin':
            return Order.objects.select_related('status', 'user').prefetch_related('items', 'status_history_entries__status', 'status_history_entries__changed_by')
        return Order.objects.select_related('status', 'user').prefetch_related('items', 'status_history_entries__status', 'status_history_entries__changed_by').filter(user=self.request.user)


def calc_delivery_cost(method, items_sum):
    """Стоимость доставки считает сервер — клиентскому значению верить нельзя."""
    if method == 'courier':
        return Decimal('0') if items_sum >= 10000 else Decimal('500')
    if method == 'post':
        return Decimal('300')
    return Decimal('0')  # самовывоз


class OrderCreateView(generics.CreateAPIView):
    """Создание заказа из корзины"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderCreateSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_object_or_404(Cart, user=request.user)

        if not cart.items.exists():
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Выбираем товары
        item_ids = serializer.validated_data.get('items', [])
        if item_ids:
            cart_items = cart.items.filter(id__in=item_ids)
        else:
            cart_items = cart.items.all()

        if not cart_items.exists():
            return Response(
                {'error': 'Нет выбранных товаров'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Блокируем строки товаров до конца транзакции — защита от гонки при списании
        cart_items = list(cart_items.select_related('product'))
        locked = {
            p.id: p for p in Product.objects.select_for_update().filter(
                id__in=[i.product_id for i in cart_items]
            )
        }

        # Проверяем наличие и активность уже под блокировкой
        for item in cart_items:
            product = locked[item.product_id]
            if not product.is_active:
                return Response(
                    {'error': f'Товар недоступен: {product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if product.stock_quantity < item.quantity:
                return Response(
                    {'error': f'Недостаточно товара: {product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Получаем статус "Оформлен"
        try:
            status_obj = OrderStatus.objects.get(name='Оформлен')
        except OrderStatus.DoesNotExist:
            return Response(
                {'error': 'Статус "Оформлен" не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items_sum = sum(locked[i.product_id].price * i.quantity for i in cart_items)
        delivery_cost = calc_delivery_cost(
            serializer.validated_data['delivery_method'], items_sum
        )

        # Создаём заказ
        order = Order.objects.create(
            user=request.user,
            city=serializer.validated_data['city'],
            address=serializer.validated_data['address'],
            postal_code=serializer.validated_data.get('postal_code', ''),
            delivery_method=serializer.validated_data['delivery_method'],
            payment_method=serializer.validated_data['payment_method'],
            delivery_cost=delivery_cost,
            comment=serializer.validated_data.get('comment', ''),
            total_amount=0,
            status=status_obj
        )

        # Создаём позиции и уменьшаем остатки
        total = Decimal('0')
        for item in cart_items:
            product = locked[item.product_id]
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=product.price,
                quantity=item.quantity
            )
            product.stock_quantity -= item.quantity
            product.save(update_fields=['stock_quantity'])
            total += product.price * item.quantity

        order.total_amount = total + delivery_cost
        order.save()

        # Удаляем выбранные товары из корзины
        cart.items.filter(id__in=[i.id for i in cart_items]).delete()

        # История статуса
        OrderStatusHistory.objects.create(
            order=order,
            status=status_obj,
            comment='Заказ оформлен',
            changed_by=request.user
        )

        # Уведомление через WebSocket (тихо no-op, если Redis недоступен)
        send_notification_to_user(
            user_id=request.user.id,
            title='Заказ оформлен!',
            message=f'Ваш заказ № {order.order_number} успешно создан',
            level='success',
            data={'order_id': order.id, 'order_number': order.order_number}
        )

        # Письмо на почту (тихо no-op, если SMTP не настроен)
        send_order_confirmation_email(order)

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )


class OrderUpdateStatusView(generics.UpdateAPIView):
    """Обновление статуса заказа (только админ)"""
    permission_classes = [IsAdminRole]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.select_related('status', 'user').prefetch_related('items', 'status_history_entries__status', 'status_history_entries__changed_by')

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        status_name = request.data.get('status')
        comment = request.data.get('comment', '')
        tracking_number = request.data.get('tracking_number', '')

        if not status_name:
            return Response(
                {'error': 'Не указан статус'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_status = OrderStatus.objects.get(name=status_name)
        except OrderStatus.DoesNotExist:
            return Response(
                {'error': f'Статус "{status_name}" не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        if tracking_number:
            order.tracking_number = tracking_number
        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            comment=comment,
            changed_by=request.user
        )

        send_order_update(order)

        return Response(OrderDetailSerializer(order).data)


class OrderStatusListView(generics.ListAPIView):
    """Список всех статусов заказов"""
    queryset = OrderStatus.objects.filter(is_active=True)
    serializer_class = OrderStatusSerializer
    pagination_class = None  # фиксированный маленький список — пагинация не нужна и ломает фронт
