import uuid
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from orders.models import Order, OrderStatus, OrderStatusHistory, CANCELLED_STATUS
from .models import Payment
from .serializers import CardPaymentSerializer
from notifications.utils import send_order_update


class ProcessPaymentView(APIView):
    """Обработка платежа (симуляция)"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CardPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Блокируем строку заказа: два одновременных запроса не оплатят его дважды
        order = get_object_or_404(
            Order.objects.select_for_update().select_related('status'),
            id=serializer.validated_data['order_id'],
            user=request.user
        )

        # Проверяем, что заказ не оплачен
        if order.payment_status:
            return Response(
                {'error': 'Заказ уже оплачен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Онлайн оплачиваются только заказы «Картой онлайн»;
        # наличные и «картой курьеру» оплачиваются при получении
        if order.payment_method != 'card':
            return Response(
                {'error': 'Этот заказ оплачивается при получении'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Отменённый заказ оплатить нельзя
        if order.status.name == CANCELLED_STATUS:
            return Response(
                {'error': 'Заказ отменён, оплатить его нельзя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Создаём или обновляем платёж
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'amount': order.total_amount,
                'payment_method': 'card',
            }
        )

        # СИМУЛЯЦИЯ: любая корректная карта проходит,
        # кроме тестовой 4444 4444 4444 4444 — она всегда отклоняется
        card_number = serializer.validated_data['card_number']

        if card_number == '4444444444444444':
            # Неуспешный платёж
            payment.status = 'failed'
            payment.save()
            return Response(
                {'error': 'Платёж отклонён банком. Проверьте данные карты.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Успешный платёж
        payment.status = 'success'
        payment.transaction_id = f'TXN-{uuid.uuid4().hex[:12].upper()}'
        payment.save()

        # Обновляем заказ. Факт оплаты сохраняем в любом случае,
        # даже если статуса «Оплачен» в базе почему-то нет
        order.payment_status = True
        paid_status = OrderStatus.objects.filter(name='Оплачен').first()
        if paid_status:
            order.status = paid_status
        order.save()

        if paid_status:
            OrderStatusHistory.objects.create(
                order=order,
                status=paid_status,
                comment=f'Платёж успешно проведён. Транзакция: {payment.transaction_id}',
                changed_by=request.user
            )

            # WebSocket-уведомление — уже после того, как транзакция зафиксируется
            transaction.on_commit(lambda: send_order_update(order))

        return Response({
            'success': True,
            'message': 'Платёж успешно проведён',
            'transaction_id': payment.transaction_id,
            'order_number': order.order_number,
        })