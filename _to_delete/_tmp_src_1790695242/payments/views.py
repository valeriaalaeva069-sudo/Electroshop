import uuid
from decimal import Decimal
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from orders.models import Order, OrderStatus, OrderStatusHistory
from .models import Payment
from .serializers import PaymentSerializer, CardPaymentSerializer
from notifications.utils import send_order_update


class ProcessPaymentView(APIView):
    """Обработка платежа (симуляция)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(
            Order,
            id=serializer.validated_data['order_id'],
            user=request.user
        )

        # Проверяем, что заказ не оплачен
        if order.payment_status:
            return Response(
                {'error': 'Заказ уже оплачен'},
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

        # СИМУЛЯЦИЯ: 95% успешных платежей
        # (для демонстрации — карта 4444 4444 4444 4444 всегда отклоняется)
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

        # Обновляем заказ
        order.payment_status = True
        try:
            paid_status = OrderStatus.objects.get(name='Оплачен')
            order.status = paid_status
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status=paid_status,
                comment=f'Платёж успешно проведён. Транзакция: {payment.transaction_id}',
                changed_by=request.user
            )

            # Отправляем WebSocket-уведомление
            send_order_update(order)

        except OrderStatus.DoesNotExist:
            pass

        return Response({
            'success': True,
            'message': 'Платёж успешно проведён',
            'transaction_id': payment.transaction_id,
            'order_number': order.order_number,
        })