from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Присоединиться к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Покинуть группу комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Получение сообщения от WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        user_id = self.scope["user"].id
        
        # Сохранить сообщение в БД
        await self.save_message(user_id, message)
        
        # Отправить сообщение в группу комнаты
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': user_id
            }
        )

    # Получение сообщения от группы комнаты
    async def chat_message(self, event):
        message = event['message']
        user_id = event['user_id']
        
        # Отправить сообщение в WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'user_id': user_id
        }))
    
    @database_sync_to_async
    def save_message(self, user_id, message):
        user = User.objects.get(id=user_id)
        room = ChatRoom.objects.get(id=self.room_id)
        Message.objects.create(
            room=room,
            sender=user,
            content=message
        )
