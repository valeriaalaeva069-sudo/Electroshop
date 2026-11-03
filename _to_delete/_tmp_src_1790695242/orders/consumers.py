import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Order


class OrderConsumer(AsyncWebsocketConsumer):
    """WebSocket для отслеживания статуса конкретного заказа"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_id = None
        self.room_group_name = None

    async def connect(self):
        # Проверяем авторизацию
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'order_{self.order_id}'

        # Проверяем, что заказ принадлежит пользователю
        order = await self.get_order()
        if not order:
            await self.close()
            return

        if order.user_id != self.scope['user'].id and not self.scope['user'].is_superuser:
            await self.close()
            return

        # Подключаемся к группе заказа
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f'✅ WebSocket заказа #{self.order_id} подключён')

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f'❌ WebSocket заказа #{self.order_id} отключён')

    async def receive(self, text_data):
        """Обработка сообщений от клиента"""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def order_update(self, event):
        """Отправка обновления статуса заказа"""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'status': event['status'],
            'status_name': event['status_name'],
            'status_color': event['status_color'],
            'comment': event.get('comment', ''),
            'tracking_number': event.get('tracking_number', ''),
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def get_order(self):
        try:
            return Order.objects.get(id=self.order_id)
        except Order.DoesNotExist:
            return None