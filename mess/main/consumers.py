import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
import traceback
from .models import ChatMessage
import re
import asyncio

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
            message_type = text_data_json.get("type", "message")
            
            # Обработка индикатора набора текста
            if message_type == "typing":
                is_typing = text_data_json.get("is_typing", False)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "typing_status",
                        "user_id": self.user.id,
                        "username": f"{self.user.first_name} {self.user.last_name}",
                        "is_typing": is_typing
                    }
                )
                return
                
            # Обработка редактирования сообщения
            elif message_type == "edit_message":
                message_id = text_data_json.get("message_id")
                message = text_data_json.get("message", "")
                
                if not message.strip() or not message_id:
                    return
                    
                # Проверка, является ли пользователь автором сообщения
                is_author = await self.check_message_author(message_id)
                if not is_author:
                    return
                    
                # Обновляем сообщение в базе данных
                edited = await self.update_message(message_id, message)
                
                # Отправляем обновление всем в группе
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "edit_message",
                        "message_id": message_id,
                        "message": message,
                        "edited": edited,
                        "sender_id": self.user.id
                    }
                )
                return
                
            # Обработка удаления сообщения
            elif message_type == "delete_message":
                message_id = text_data_json.get("message_id")
                
                if not message_id:
                    logger.warning("Получен запрос на удаление без ID сообщения")
                    return
                
                logger.info(f"Запрос на удаление сообщения {message_id} от {self.user.username}")
                
                try:
                    # Проверяем, существует ли сообщение и является ли пользователь его автором
                    message = await self.delete_message_if_author(message_id)
                    
                    if message:
                        # Просто отправляем всем событие удаления
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "delete_message",
                                "message_id": str(message_id),  # Преобразуем в строку для совместимости
                                "sender_id": self.user.id
                            }
                        )
                        
                        logger.info(f"Сообщение {message_id} удалено и отправлено уведомление всем в комнате")
                    else:
                        logger.warning(f"Сообщение {message_id} не найдено или пользователь не является автором")
                except Exception as e:
                    logger.error(f"Ошибка при удалении сообщения: {str(e)}")
                
                return
                
            # Обработка обычного сообщения
            message = text_data_json.get("message", "")
            
            if not message.strip():
                return
            
            logger.info(f"Получено сообщение от {self.user.username} в комнате {self.room_name}")
            
            # Сохранение сообщения в базу данных и получение его ID
            message_id = await self.save_message(message)
            
            # Отправка сообщения в группу комнаты
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": self.user.username,
                    "sender_id": self.user.id,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": message_id
                }
            )
            
            # Отправляем обновление всем пользователям, у которых открыта личная группа получателя
            # для обновления счетчика непрочитанных сообщений в реальном времени
            direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', self.room_name)
            if direct_chat_match:
                user_id1 = int(direct_chat_match.group(1))
                user_id2 = int(direct_chat_match.group(2))
                
                # Определяем получателя
                recipient_id = user_id1 if self.user.id == user_id2 else user_id2
                
                # Отправляем обновление в группу уведомлений получателя
                await self.channel_layer.group_send(
                    f"notifications_user_{recipient_id}",
                    {
                        "type": "notification_message",
                        "notification_type": "new_message",
                        "room_name": self.room_name
                    }
                )
            
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
            message_id = event.get("message_id", None)
            
            # Отправка сообщения клиенту
            await self.send(text_data=json.dumps({
                "message": message,
                "sender": sender,
                "sender_id": sender_id,
                "timestamp": timestamp,
                "message_id": message_id
            }))
            
            logger.info(f"Отправлено сообщение в комнату {self.room_name}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {str(e)}")
            logger.error(traceback.format_exc())
    
    @database_sync_to_async
    def save_message(self, message):
        """
        Сохранение сообщения в базу данных и возврат его ID
        """
        try:
            chat_message = ChatMessage.objects.create(
                room_name=self.room_name,
                user=self.user,
                message=message
            )
            logger.info(f"Сообщение от {self.user.username} сохранено в базу данных с ID {chat_message.id}")
            return chat_message.id
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def typing_status(self, event):
        """
        Отправка статуса набора текста клиенту
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "typing_status",
                "user_id": event["user_id"],
                "username": event["username"],
                "is_typing": event["is_typing"]
            }))
        except Exception as e:
            logger.error(f"Ошибка отправки статуса набора текста: {str(e)}")
    
    async def edit_message(self, event):
        """
        Отправка обновленного сообщения клиенту
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "edit_message",
                "message_id": event["message_id"],
                "message": event["message"],
                "edited": event["edited"],
                "sender_id": event["sender_id"]
            }))
        except Exception as e:
            logger.error(f"Ошибка отправки обновленного сообщения: {str(e)}")
    
    async def delete_message(self, event):
        """
        Отправка информации об удаленном сообщении клиенту
        """
        try:
            # Просто передаем данные клиенту без лишней обработки
            message_id = event.get('message_id')
            
            logger.info(f"Отправка клиенту {self.user.username} уведомления об удалении сообщения {message_id}")
            
            # Отправляем минимально необходимые данные
            await self.send(text_data=json.dumps({
                "type": "delete_message",
                "message_id": message_id
            }))
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об удалении: {str(e)}")
    
    @database_sync_to_async
    def check_message_author(self, message_id):
        """
        Проверка, является ли текущий пользователь автором сообщения
        """
        try:
            message = ChatMessage.objects.filter(id=message_id).first()
            
            if not message:
                logger.warning(f"Сообщение с ID {message_id} не найдено при проверке автора")
                return False
                
            is_author = message.user.id == self.user.id
            
            if not is_author:
                logger.warning(f"Пользователь {self.user.username} не является автором сообщения {message_id}")
                
            return is_author
        except Exception as e:
            logger.error(f"Ошибка при проверке автора сообщения: {str(e)}")
            return False
    
    @database_sync_to_async
    def update_message(self, message_id, new_text):
        """
        Обновление сообщения в базе данных
        """
        try:
            message = ChatMessage.objects.filter(id=message_id).first()
            
            if not message:
                logger.warning(f"Сообщение с ID {message_id} не найдено при обновлении")
                return False
                
            message.message = new_text
            message.edited = True
            message.save()
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
            return False
    
    @database_sync_to_async
    def delete_message(self, message_id):
        """
        Удаление сообщения из базы данных
        """
        try:
            message = ChatMessage.objects.filter(id=message_id).first()
            
            if not message:
                logger.warning(f"Сообщение с ID {message_id} не найдено при удалении")
                return False
                
            logger.info(f"Удаление сообщения ID={message_id} от пользователя {message.user.username}")
            
            message.delete()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {str(e)}")
            return False

    @database_sync_to_async
    def get_message_info(self, message_id):
        """
        Получение информации о сообщении
        """
        try:
            message = ChatMessage.objects.filter(id=message_id).first()
            
            if not message:
                logger.warning(f"Сообщение с ID {message_id} не найдено при получении информации")
                return None
            
            # Вернуть основную информацию о сообщении для использования в WebSocket событии
            return {
                'id': message.id,
                'user_id': message.user.id,
                'username': message.user.username, 
                'text': message.message,
                'timestamp': message.timestamp.isoformat() if message.timestamp else '',
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о сообщении: {str(e)}")
            return None

    @database_sync_to_async
    def delete_message_if_author(self, message_id):
        """
        Удаление сообщения из базы данных, если пользователь является автором
        """
        try:
            message = ChatMessage.objects.filter(id=message_id).first()
            
            if not message:
                logger.warning(f"Сообщение с ID {message_id} не найдено при удалении")
                return None
                
            if message.user.id != self.user.id:
                logger.warning(f"Пользователь {self.user.username} не является автором сообщения {message_id}")
                return None
                
            logger.info(f"Удаление сообщения ID={message_id} от пользователя {message.user.username}")
            
            message.delete()
            return message
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {str(e)}")
            return None


class NotificationsConsumer(AsyncWebsocketConsumer):
    """
    Consumer для обработки уведомлений о новых сообщениях
    """
    
    async def connect(self):
        """
        Обработка подключения клиента
        """
        self.user = self.scope["user"]
        
        # Проверка аутентификации
        if isinstance(self.user, AnonymousUser):
            logger.warning(f"Отклонено неаутентифицированное подключение к уведомлениям")
            await self.close(code=4001)  # Отказ в подключении
            return
        
        # Создаем персональную группу для пользователя
        self.user_group_name = f"notifications_user_{self.user.id}"
        
        logger.info(f"Пользователь {self.user.username} подключается к каналу уведомлений")
        
        # Добавление пользователя в его персональную группу
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Принять соединение
        await self.accept()
        
    async def disconnect(self, close_code):
        """
        Обработка отключения клиента
        """
        if hasattr(self, 'user_group_name') and hasattr(self, 'channel_name'):
            # Удаление пользователя из группы
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
            logger.info(f"Пользователь отключился от канала уведомлений, код: {close_code}")
    
    async def notification_message(self, event):
        """
        Отправка уведомления клиенту
        """
        try:
            # Отправка уведомления клиенту
            await self.send(text_data=json.dumps({
                "notification_type": event.get("notification_type"),
                "room_name": event.get("room_name")
            }))
            
            logger.info(f"Отправлено уведомление пользователю {self.user.username}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {str(e)}")
            logger.error(traceback.format_exc()) 