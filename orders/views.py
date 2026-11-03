from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.db import transaction
from products.models import Product
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from notifications.utils import send_order_update, send_notification_to_user
from users.permissions import IsAdminRole, is_shop_admin
from .emails import send_order_confirmation_email
from .receipt import build_receipt_pdf
from .models import (
    Order, OrderItem, OrderStatus, OrderStatusHistory,
    CANCELLED_STATUS, return_items_to_stock,
)
from .serializers import (
    OrderSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderStatusSerializer,
)
from cart.models import Cart


def orders_queryset():
    return Order.objects.select_related('status', 'user').prefetch_related(
        'items', 'status_history_entries__status', 'status_history_entries__changed_by'
    )


class OrderListView(generics.ListAPIView):
    """Заказы текущего пользователя.
    Админ получает заказы всех покупателей только явно: /api/orders/?scope=all
    (это нужно админ-панели), а в «Моих заказах» и профиле видит только свои."""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        if self.request.query_params.get('scope') == 'all' and is_shop_admin(self.request.user):
            return orders_queryset()
        return orders_queryset().filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    """Детали заказа (свой заказ; админ может открыть любой)"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        if is_shop_admin(self.request.user):
            return orders_queryset()
        return orders_queryset().filter(user=self.request.user)


class OrderReceiptView(generics.GenericAPIView):
    """PDF-чек по заказу (свой заказ; админ может скачать любой)"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = orders_queryset()
        return qs if is_shop_admin(self.request.user) else qs.filter(user=self.request.user)

    def get(self, request, pk):
        order = get_object_or_404(self.get_queryset(), pk=pk)
        response = HttpResponse(build_receipt_pdf(order), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt-{order.order_number}.pdf"'
        return response


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

        cart = Cart.objects.filter(user=request.user).first()

        if cart is None or not cart.items.exists():
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

        # Уведомление и письмо — только после фиксации транзакции:
        # иначе SMTP-отправка шла бы, пока строки товаров заблокированы,
        # а при откате пользователь получил бы письмо о несуществующем заказе.
        user_id = request.user.id

        def notify():
            # WebSocket-уведомление (тихо no-op, если канал недоступен)
            send_notification_to_user(
                user_id=user_id,
                title='Заказ оформлен!',
                message=f'Ваш заказ № {order.order_number} успешно создан',
                level='success',
                data={'order_id': order.id, 'order_number': order.order_number}
            )
            # Письмо на почту (тихо no-op, если SMTP не настроен)
            send_order_confirmation_email(order)

        transaction.on_commit(notify)

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )


class OrderUpdateStatusView(generics.UpdateAPIView):
    """Обновление статуса заказа (только админ)"""
    permission_classes = [IsAdminRole]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return orders_queryset()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Блокируем заказ, чтобы два админа одновременно не отменили его дважды
        order = get_object_or_404(
            Order.objects.select_for_update().select_related('status', 'user'),
            pk=kwargs['pk']
        )
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

        old_status_name = order.status.name
        if old_status_name == CANCELLED_STATUS and new_status.name != CANCELLED_STATUS:
            return Response(
                {'error': 'Заказ отменён: товар уже вернулся на склад, менять статус нельзя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # При отмене возвращаем товар на склад (один раз)
        if new_status.name == CANCELLED_STATUS and old_status_name != CANCELLED_STATUS:
            return_items_to_stock(order)

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

        transaction.on_commit(lambda: send_order_update(order))

        return Response(OrderDetailSerializer(order).data)


class OrderStatusListView(generics.ListAPIView):
    """Список всех статусов заказов"""
    queryset = OrderStatus.objects.filter(is_active=True)
    serializer_class = OrderStatusSerializer
    pagination_class = None  # фиксированный маленький список — пагинация не нужна и ломает фронт
