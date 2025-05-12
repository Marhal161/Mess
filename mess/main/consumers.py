import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
import traceback
from .models import ChatMessage, GroupChat
import re
import asyncio
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer для обработки WebSocket соединений чата
    """
    
    async def connect(self):
        """
        Установка соединения
        """
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Проверяем, является ли это групповым чатом
        is_group_chat = self.room_name.startswith('group_')
        
        if is_group_chat:
            # Для групповых чатов проверяем, является ли пользователь участником
            try:
                chat_id = int(self.room_name.split('_')[1])
                group_chat = await database_sync_to_async(GroupChat.objects.get)(id=chat_id)
                
                # Правильно проверяем членство в групповом чате
                is_member = await self.check_group_chat_membership(group_chat, self.scope['user'].id)
                
                if not is_member:
                    logger.warning(f"Пользователь {self.scope['user'].username} не является участником группового чата {chat_id}")
                    await self.close()
                    return
            except (GroupChat.DoesNotExist, ValueError, IndexError) as e:
                logger.error(f"Ошибка при проверке группового чата: {str(e)}")
                await self.close()
                return
        else:
            # Для личных чатов проверяем, является ли пользователь участником
            try:
                user_ids = [int(id) for id in self.room_name.split('_')[1:]]
                if self.scope['user'].id not in user_ids:
                    logger.warning(f"Пользователь {self.scope['user'].username} не является участником личного чата {self.room_name}")
                    await self.close()
                    return
            except (ValueError, IndexError) as e:
                logger.error(f"Ошибка при проверке личного чата: {str(e)}")
                await self.close()
                return
        
        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем уведомление о подключении
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f"{self.scope['user'].username} присоединился к чату",
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                    'first_name': self.scope['user'].first_name,
                    'last_name': self.scope['user'].last_name,
                    'avatar': self.scope['user'].avatar.url if hasattr(self.scope['user'], 'avatar') and self.scope['user'].avatar else None
                },
                'is_system': True
            }
        )
    
    async def disconnect(self, close_code):
        """
        Закрытие соединения
        """
        # Отправляем уведомление об отключении
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': f"{self.scope['user'].username} покинул чат",
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                    'first_name': self.scope['user'].first_name,
                    'last_name': self.scope['user'].last_name,
                    'avatar': self.scope['user'].avatar.url if hasattr(self.scope['user'], 'avatar') and self.scope['user'].avatar else None
                },
                'is_system': True
            }
        )
        
        # Удаляем из группы комнаты
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Получение сообщения
        """
        try:
            # Логируем все входящие данные для отладки
            logger.info(f"WebSocket получен: {text_data[:100]}")
            
            text_data_json = json.loads(text_data)
            
            # Получаем тип сообщения, по умолчанию 'message'
            message_type = text_data_json.get('type', 'message')
            
            # Обрабатываем разные типы сообщений
            if message_type == 'message' and 'message' in text_data_json:
                # Обычное текстовое сообщение
                await self.handle_chat_message(text_data_json['message'])
            elif message_type == 'typing':
                # Сигнал о наборе текста
                await self.handle_typing(text_data_json.get('is_typing', False))
            else:
                # Неизвестный тип сообщения, или отсутствует ключ 'message'
                logger.warning(f"Получено сообщение неизвестного типа или без контента: {text_data_json}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
            logger.error(f"Полученные данные: {text_data}")
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def handle_chat_message(self, message):
        """
        Обработка обычного текстового сообщения
        """
        # Отправляем сообщение в группу немедленно, до сохранения в БД
        # Это ускорит отображение на фронтенде
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'message_id': None,  # ID будет отсутствовать, но это не критично
                'timestamp': datetime.now().isoformat(),
                'user': {
                    'id': self.scope['user'].id,
                    'username': self.scope['user'].username,
                    'first_name': self.scope['user'].first_name,
                    'last_name': self.scope['user'].last_name,
                    'avatar': self.scope['user'].avatar.url if hasattr(self.scope['user'], 'avatar') and self.scope['user'].avatar else None
                },
                'is_system': False
            }
        )
        
        # Создаем новое сообщение в БД асинхронно
        asyncio.create_task(self.save_message_to_db(message))
    
    async def handle_typing(self, is_typing):
        """
        Обработка сигнала о наборе текста
        """
        # Отправляем статус набора текста всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': self.scope['user'].id,
                'username': self.scope['user'].username,
                'is_typing': is_typing
            }
        )
    
    async def save_message_to_db(self, message):
        """
        Асинхронно сохраняем сообщение в БД и отправляем обновленное сообщение
        """
        # Сохраняем сообщение в базу данных
        message_id = await self.save_message(message)
        
        # Проверяем, успешно ли сохранено сообщение
        if message_id:
            # Если сообщение сохранено успешно, отправляем обновленную информацию с ID сообщения
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'message_id': message_id,
                    'timestamp': datetime.now().isoformat(),
                    'user': {
                        'id': self.scope['user'].id,
                        'username': self.scope['user'].username,
                        'first_name': self.scope['user'].first_name,
                        'last_name': self.scope['user'].last_name,
                        'avatar': self.scope['user'].avatar.url if hasattr(self.scope['user'], 'avatar') and self.scope['user'].avatar else None
                    },
                    'is_system': False
                }
            )
        else:
            logger.error(f"Не удалось сохранить сообщение в БД")
    
    async def chat_message(self, event):
        """
        Отправка сообщения клиенту
        """
        try:
            # Подготавливаем информацию для отправки клиенту
            message_data = {
                'type': 'chat_message',
                'message': event.get('message', ''),
                'sender': event.get('user', {}).get('username', ''),
                'sender_id': event.get('user', {}).get('id', None),
                'timestamp': event.get('timestamp', datetime.now().isoformat()),
                'message_id': event.get('message_id', None),
                'is_system': event.get('is_system', False),
                'edited': event.get('edited', False),
                'first_name': event.get('user', {}).get('first_name', ''),
                'last_name': event.get('user', {}).get('last_name', ''),
                'avatar': event.get('user', {}).get('avatar', None)
            }
            
            # Логируем информацию об аватаре для отладки
            logger.info(f"Отправка сообщения с аватаром: {message_data['avatar']}")
            
            # Отправляем данные клиенту
            await self.send(text_data=json.dumps(message_data))
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения клиенту: {str(e)}")

    @database_sync_to_async
    def save_message(self, message):
        """
        Сохранение сообщения в базу данных и возврат его ID
        """
        try:
            chat_message = ChatMessage.objects.create(
                room_name=self.room_name,
                user=self.scope['user'],
                message=message
            )
            
            # Если это групповой чат, связываем сообщение с чатом
            if self.room_name.startswith('group_'):
                try:
                    chat_id = int(self.room_name.split('_')[1])
                    group_chat = GroupChat.objects.get(id=chat_id)
                    chat_message.group_chat = group_chat
                    chat_message.save()
                except Exception as e:
                    logger.error(f"Ошибка при связывании сообщения с групповым чатом: {str(e)}")
            
            logger.info(f"Сообщение от {self.scope['user'].username} сохранено в базу данных с ID {chat_message.id}")
            
            # Отправляем уведомление о новом сообщении в канал уведомлений
            try:
                channel_layer = get_channel_layer()
                asyncio.run_coroutine_threadsafe(
                    channel_layer.group_send(
                        'notifications',
                        {
                            'type': 'notification',
                            'notification_type': 'new_message',
                            'room_name': self.room_name,
                            'message': message,
                            'user': {
                                'id': self.scope['user'].id,
                                'username': self.scope['user'].username
                            }
                        }
                    ),
                    asyncio.get_event_loop()
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления о новом сообщении: {str(e)}")
            
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
            
            logger.info(f"Отправка клиенту {self.scope['user'].username} уведомления об удалении сообщения {message_id}")
            
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
                
            is_author = message.user.id == self.scope['user'].id
            
            if not is_author:
                logger.warning(f"Пользователь {self.scope['user'].username} не является автором сообщения {message_id}")
                
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
                
            if message.user.id != self.scope['user'].id:
                logger.warning(f"Пользователь {self.scope['user'].username} не является автором сообщения {message_id}")
                return None
                
            logger.info(f"Удаление сообщения ID={message_id} от пользователя {message.user.username}")
            
            message.delete()
            return message
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {str(e)}")
            return None

    @database_sync_to_async
    def check_group_chat_membership(self, group_chat, user_id):
        """
        Проверяет, является ли пользователь участником группового чата
        """
        try:
            return group_chat.members.filter(id=user_id).exists()
        except Exception as e:
            logger.error(f"Ошибка при проверке членства в групповом чате: {str(e)}")
            return False


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