import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_notification_to_user(user_id, title, message, level='info', data=None):
    """Отправка персонального уведомления пользователю.

    Не должна ронять вызывающий код, если Redis/Channels недоступны —
    в таком случае уведомление просто не уйдёт (об этом пишем в лог).
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning('Channel layer не настроен — уведомление не отправлено')
            return

        group_name = f'notifications_{user_id}'

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_notification',
                'title': title,
                'message': message,
                'level': level,
                'timestamp': timezone.now().isoformat(),
                'data': data or {},
            }
        )
    except Exception as e:
        logger.warning(f'Не удалось отправить уведомление (Redis недоступен?): {e}')


def send_order_update(order):
    """Отправка обновления статуса заказа.

    Так же безопасна к отсутствию Redis/Channels — при ошибке просто
    логируем и продолжаем работу.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning('Channel layer не настроен — обновление заказа не отправлено')
        else:
            # 1. Отправляем в группу заказа (для страницы заказа)
            async_to_sync(channel_layer.group_send)(
                f'order_{order.id}',
                {
                    'type': 'order_update',
                    'status': order.status.name,
                    'status_name': order.status.name,
                    'status_color': order.status.color,
                    'comment': f'Статус изменён на "{order.status.name}"',
                    'tracking_number': order.tracking_number,
                    'timestamp': timezone.now().isoformat(),
                }
            )
    except Exception as e:
        logger.warning(f'Не удалось отправить обновление заказа (Redis недоступен?): {e}')

    # 2. Отправляем персональное уведомление пользователю
    send_notification_to_user(
        user_id=order.user.id,
        title=f'Заказ № {order.order_number}',
        message=f'Статус изменён на "{order.status.name}"',
        level='info',
        data={
            'order_id': order.id,
            'order_number': order.order_number,
            'status': order.status.name,
        }
    )
