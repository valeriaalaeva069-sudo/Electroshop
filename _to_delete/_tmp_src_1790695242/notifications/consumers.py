import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket для персональных уведомлений пользователя"""

    async def connect(self):
        # Проверяем авторизацию
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.user_id = self.scope['user'].id
        self.room_group_name = f'notifications_{self.user_id}'

        # Подключаемся к персональной группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f'✅ WebSocket подключён: user_{self.user_id}')

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f'❌ WebSocket отключён: user_{self.user_id}')

    async def receive(self, text_data):
        """Обработка сообщений от клиента"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    # === Обработчики сообщений от сервера ===

    async def send_notification(self, event):
        """Отправка уведомления пользователю"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'level': event.get('level', 'info'),  # info / success / warning / error
            'timestamp': event['timestamp'],
            'data': event.get('data', {}),
        }))

    async def order_update(self, event):
        """Уведомление об изменении статуса заказа"""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event['order_id'],
            'order_number': event['order_number'],
            'status': event['status'],
            'status_color': event['status_color'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))