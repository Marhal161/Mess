import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
import traceback
from .models import ChatMessage

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer для обработки WebSocket соединений чата
    """
    
    async def connect(self):
        """
        Обработка подключения клиента
        """
        self.user = self.scope["user"]
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        
        # Проверка аутентификации
        if isinstance(self.user, AnonymousUser):
            logger.warning(f"Отклонено неаутентифицированное подключение к комнате {self.room_name}")
            await self.close(code=4001)  # Отказ в подключении
            return
        
        logger.info(f"Пользователь {self.user.username} подключается к комнате {self.room_name}")
        
        # Добавление пользователя в группу комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Принять соединение
        await self.accept()
        
        # Отправить уведомление о входе пользователя в комнату
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": f"{self.user.username} присоединился к чату",
                "sender": "system",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def disconnect(self, close_code):
        """
        Обработка отключения клиента
        """
        if hasattr(self, 'room_group_name') and hasattr(self, 'channel_name'):
            # Удаление пользователя из группы комнаты
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            if not isinstance(self.user, AnonymousUser):
                # Отправка уведомления о выходе пользователя
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": f"{self.user.username} покинул чат",
                        "sender": "system",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            logger.info(f"Пользователь отключился от комнаты {self.room_name}, код: {close_code}")
    
    async def receive(self, text_data):
        """
        Получение сообщения от клиента
        """
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get("message", "")
            
            if not message.strip():
                return
            
            logger.info(f"Получено сообщение от {self.user.username} в комнате {self.room_name}")
            
            # Отправка сообщения в группу комнаты
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": self.user.username,
                    "sender_id": self.user.id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Сохранение сообщения в базу данных
            await self.save_message(message)
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def chat_message(self, event):
        """
        Отправка сообщения клиенту
        """
        try:
            message = event["message"]
            sender = event.get("sender", "unknown")
            sender_id = event.get("sender_id", None)
            timestamp = event.get("timestamp", datetime.now().isoformat())
            
            # Отправка сообщения клиенту
            await self.send(text_data=json.dumps({
                "message": message,
                "sender": sender,
                "sender_id": sender_id,
                "timestamp": timestamp
            }))
            
            logger.info(f"Отправлено сообщение в комнату {self.room_name}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {str(e)}")
            logger.error(traceback.format_exc())
    
    @database_sync_to_async
    def save_message(self, message):
        """
        Сохранение сообщения в базу данных
        """
        try:
            ChatMessage.objects.create(
                room_name=self.room_name,
                user=self.user,
                message=message
            )
            logger.info(f"Сообщение от {self.user.username} сохранено в базу данных")
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {str(e)}")
            logger.error(traceback.format_exc()) 