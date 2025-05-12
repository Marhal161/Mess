from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import ChatMessage, User, ChatReport, GroupChat
from ..decorators import check_auth_tokens, check_auth_tokens_api
from django.utils.decorators import method_decorator
import logging
import re
from django.db.models import Q, Max, F, Subquery, OuterRef
from django.db.models.functions import Coalesce
import traceback
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

class ChatMessagesAPI(APIView):
    """
    API для получения истории сообщений чата
    """
    
    @method_decorator(check_auth_tokens)
    def get(self, request, room_name):
        """
        Получение истории сообщений для указанной комнаты
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Если это личный чат, проверяем, является ли пользователь участником
            direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
            if direct_chat_match:
                user_id1 = int(direct_chat_match.group(1))
                user_id2 = int(direct_chat_match.group(2))
                
                if request.user.id not in [user_id1, user_id2]:
                    return Response(
                        {"detail": "У вас нет доступа к этому чату"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Получаем все сообщения для комнаты, отсортированные по времени
            messages = ChatMessage.objects.filter(
                room_name=room_name
            ).order_by('timestamp')
            
            # Отмечаем сообщения как прочитанные
            for msg in messages:
                if msg.user.id != request.user.id:  # Не отмечаем свои сообщения
                    msg.read_by.add(request.user)
            
            # Сериализуем сообщения
            serialized_messages = []
            for msg in messages:
                serialized_messages.append({
                    'id': msg.id,
                    'message': msg.message,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_read': request.user in msg.read_by.all(),
                    'edited': msg.edited,
                    'user': {
                        'id': msg.user.id,
                        'username': msg.user.username,
                        'first_name': msg.user.first_name,
                        'last_name': msg.user.last_name,
                        'avatar': msg.user.avatar.url if msg.user.avatar else None
                    }
                })
            
            return Response({
                'messages': serialized_messages,
                'room_name': room_name
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории сообщений: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении истории сообщений"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChatListAPI(APIView):
    """
    API для получения списка чатов с последними сообщениями
    """
    
    @method_decorator(check_auth_tokens)
    def get(self, request):
        """
        Получение списка чатов пользователя с последними сообщениями
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Найдем все личные чаты пользователя (по шаблону direct_X_Y)
            user_id = request.user.id
            
            # Шаблоны для личных чатов с участием пользователя
            pattern1 = f'direct_{user_id}_\\d+'
            pattern2 = f'direct_\\d+_{user_id}'
            
            # Получаем все уникальные комнаты, в которых участвовал пользователь
            user_chat_rooms = ChatMessage.objects.filter(
                Q(room_name__regex=pattern1) | Q(room_name__regex=pattern2)
            ).values_list('room_name', flat=True).distinct()
            
            # Подготавливаем результат
            direct_chats = []
            processed_user_ids = set()  # Отслеживаем ID собеседников, чтобы избежать дубликатов
            
            for room_name in user_chat_rooms:
                direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
                if direct_chat_match:
                    user_id1 = int(direct_chat_match.group(1))
                    user_id2 = int(direct_chat_match.group(2))
                    
                    # Определяем собеседника
                    other_user_id = user_id1 if request.user.id == user_id2 else user_id2
                    
                    # Проверяем, не обрабатывали ли мы уже этого пользователя
                    if other_user_id in processed_user_ids:
                        continue
                        
                    # Добавляем ID в список обработанных
                    processed_user_ids.add(other_user_id)
                    
                    try:
                        other_user = User.objects.get(id=other_user_id)
                        
                        # Получаем последнее сообщение в чате
                        last_message = ChatMessage.objects.filter(
                            room_name=room_name
                        ).order_by('-timestamp').first()
                        
                        # Проверяем, есть ли непрочитанные сообщения
                        unread_count = ChatMessage.objects.filter(
                            room_name=room_name
                        ).exclude(
                            user=request.user
                        ).exclude(
                            read_by=request.user
                        ).count()
                        
                        # Добавляем данные о чате
                        direct_chats.append({
                            'id': room_name,
                            'name': f"{other_user.first_name} {other_user.last_name}",
                            'user': {
                                'id': other_user.id,
                                'username': other_user.username,
                                'first_name': other_user.first_name,
                                'last_name': other_user.last_name,
                                'avatar': other_user.avatar.url if other_user.avatar else None
                            },
                            'last_message': last_message.message if last_message else '',
                            'last_message_time': last_message.timestamp.isoformat() if last_message else None,
                            'unread_count': unread_count
                        })
                    except User.DoesNotExist:
                        logger.warning(f"Пользователь с ID {other_user_id} не найден")
            
            # Сортируем личные чаты по времени последнего сообщения (новые сверху)
            direct_chats = sorted(
                direct_chats, 
                key=lambda x: x['last_message_time'] if x['last_message_time'] else '0', 
                reverse=True
            )
            
            return Response({
                'direct_chats': direct_chats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка чатов: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении списка чатов"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UnreadMessagesCountAPI(APIView):
    """
    API для получения количества непрочитанных сообщений
    """
    
    @method_decorator(check_auth_tokens)
    def get(self, request):
        """
        Получение количества непрочитанных сообщений для текущего пользователя
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Найдем все личные чаты пользователя (по шаблону direct_X_Y)
            user_id = request.user.id
            
            # Шаблоны для личных чатов с участием пользователя
            pattern1 = f'direct_{user_id}_\\d+'
            pattern2 = f'direct_\\d+_{user_id}'
            
            # Находим все сообщения в личных чатах с участием пользователя, 
            # которые не были прочитаны пользователем и не были отправлены пользователем
            unread_messages = ChatMessage.objects.filter(
                Q(room_name__regex=pattern1) | Q(room_name__regex=pattern2)  # В личных чатах с участием пользователя
            ).exclude(
                user=request.user  # Исключаем сообщения от текущего пользователя
            ).exclude(
                read_by=request.user  # Исключаем сообщения, прочитанные текущим пользователем
            )
            
            # Получаем количество непрочитанных сообщений
            unread_count = unread_messages.count()
            
            # Получаем информацию о чатах с непрочитанными сообщениями
            unread_chats = {}
            for msg in unread_messages:
                if msg.room_name not in unread_chats:
                    unread_chats[msg.room_name] = 1
                else:
                    unread_chats[msg.room_name] += 1
            
            return Response({
                'total_unread': unread_count,
                'unread_chats': unread_chats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении количества непрочитанных сообщений: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении количества непрочитанных сообщений"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MarkMessagesAsReadAPI(APIView):
    """
    API для отметки сообщений как прочитанных
    """
    
    @method_decorator(check_auth_tokens)
    def post(self, request, room_name):
        """
        Отметить все сообщения в комнате как прочитанные
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Если это личный чат, проверяем, является ли пользователь участником
            direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
            if direct_chat_match:
                user_id1 = int(direct_chat_match.group(1))
                user_id2 = int(direct_chat_match.group(2))
                
                if request.user.id not in [user_id1, user_id2]:
                    return Response(
                        {"detail": "У вас нет доступа к этому чату"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Получаем все непрочитанные сообщения в комнате, которые не от текущего пользователя
            messages = ChatMessage.objects.filter(
                room_name=room_name
            ).exclude(
                user=request.user  # Исключаем сообщения от текущего пользователя
            ).exclude(
                read_by=request.user  # Исключаем сообщения, прочитанные текущим пользователем
            )
            
            # Отмечаем сообщения как прочитанные
            for msg in messages:
                msg.read_by.add(request.user)
            
            return Response({
                'status': 'success',
                'marked_as_read': messages.count(),
                'room_name': room_name
            })
            
        except Exception as e:
            logger.error(f"Ошибка при отметке сообщений как прочитанных: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при отметке сообщений как прочитанных"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EditMessageAPI(APIView):
    """
    API для редактирования сообщений
    """
    
    @method_decorator(check_auth_tokens)
    def post(self, request, message_id):
        """
        Редактирование сообщения по ID
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Получаем новый текст сообщения из запроса
            new_message_text = request.data.get('message', '')
            if not new_message_text.strip():
                return Response(
                    {"detail": "Текст сообщения не может быть пустым"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Находим сообщение по ID
            try:
                message = ChatMessage.objects.get(id=message_id)
            except ChatMessage.DoesNotExist:
                return Response(
                    {"detail": "Сообщение не найдено"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Проверяем, является ли пользователь автором сообщения
            if message.user.id != request.user.id:
                return Response(
                    {"detail": "Вы не можете редактировать чужие сообщения"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Обновляем текст сообщения
            message.message = new_message_text
            message.edited = True  # Отмечаем что сообщение было отредактировано
            message.save()
            
            return Response({
                'status': 'success',
                'message': 'Сообщение успешно отредактировано',
                'message_id': message_id
            })
            
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при редактировании сообщения"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeleteMessageAPI(APIView):
    """
    API для удаления сообщений
    """
    
    @method_decorator(check_auth_tokens)
    def post(self, request, message_id):
        """
        Удаление сообщения по ID
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Находим сообщение по ID
            try:
                message = ChatMessage.objects.get(id=message_id)
            except ChatMessage.DoesNotExist:
                return Response(
                    {"detail": "Сообщение не найдено", "status": "error"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Проверяем, является ли пользователь автором сообщения
            if message.user.id != request.user.id:
                return Response(
                    {"detail": "Вы не можете удалять чужие сообщения", "status": "error"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Сохраняем ID комнаты перед удалением
            room_name = message.room_name
            
            # Сохраняем информацию о сообщении для логирования
            message_info = {
                'id': message.id,
                'text': message.message,
                'user': message.user.username,
                'room': message.room_name,
                'timestamp': message.timestamp.isoformat()
            }
            
            # Удаляем сообщение
            message.delete()
            
            # Записываем лог успешного удаления
            logger.info(f"Успешно удалено сообщение ID={message_id}, текст: '{message_info['text'][:30]}...' из комнаты {room_name}")
            
            return Response({
                'status': 'success',
                'message': 'Сообщение успешно удалено',
                'message_id': message_id,
                'room_name': room_name
            })
            
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {message_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": "Произошла ошибка при удалении сообщения", "status": "error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ReportChatAPI(APIView):
    """
    API для отправки жалобы на чат
    """
    
    @method_decorator(check_auth_tokens)
    def post(self, request, room_name):
        """
        Создание жалобы на чат
        """
        try:
            # Проверяем аутентификацию
            if not request.user.is_authenticated:
                return Response(
                    {"detail": "Пользователь не аутентифицирован"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Получаем описание проблемы из запроса
            description = request.data.get('description', '')
            
            if not description.strip():
                return Response(
                    {"detail": "Необходимо описать проблему"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Если это личный чат, проверяем, является ли пользователь участником
            direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
            if direct_chat_match:
                user_id1 = int(direct_chat_match.group(1))
                user_id2 = int(direct_chat_match.group(2))
                
                if request.user.id not in [user_id1, user_id2]:
                    return Response(
                        {"detail": "У вас нет доступа к этому чату"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Создаем новую жалобу
            report = ChatReport(
                reporter=request.user,
                room_name=room_name,
                description=description
            )
            report.save()
            
            logger.info(f"Пользователь {request.user.username} отправил жалобу на чат {room_name}")
            
            return Response({
                'status': 'success',
                'message': 'Жалоба успешно отправлена',
                'report_id': report.id
            })
            
        except Exception as e:
            logger.error(f"Ошибка при отправке жалобы на чат: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": "Произошла ошибка при отправке жалобы"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GroupChatAPI(APIView):
    """
    API для управления групповыми чатами
    """
    
    @method_decorator(check_auth_tokens_api)
    def get(self, request, *args, **kwargs):
        """
        Получение списка групповых чатов пользователя
        """
        try:
            # Получаем все групповые чаты, где пользователь является участником
            group_chats = GroupChat.objects.filter(
                members=request.user
            ).prefetch_related('members', 'messages')
            
            # Сериализуем чаты
            serialized_chats = []
            for chat in group_chats:
                last_message = chat.messages.order_by('-timestamp').first()
                unread_count = chat.messages.exclude(
                    user=request.user
                ).exclude(
                    read_by=request.user
                ).count()
                
                serialized_chats.append({
                    'id': chat.id,
                    'name': chat.name,
                    'description': chat.description,
                    'is_private': chat.is_private,
                    'avatar': chat.avatar.url if chat.avatar else None,
                    'room_name': f"group_{chat.id}",
                    'created_by': {
                        'id': chat.created_by.id,
                        'username': chat.created_by.username,
                        'first_name': chat.created_by.first_name,
                        'last_name': chat.created_by.last_name
                    },
                    'members_count': chat.members.count(),
                    'members': [{
                        'id': member.id,
                        'username': member.username,
                        'first_name': member.first_name,
                        'last_name': member.last_name
                    } for member in chat.members.all()],
                    'last_message': last_message.message if last_message else None,
                    'last_message_time': last_message.timestamp.isoformat() if last_message else None,
                    'unread_count': unread_count
                })
            
            return Response({
                'group_chats': serialized_chats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка групповых чатов: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении списка групповых чатов"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @method_decorator(check_auth_tokens_api)
    def post(self, request):
        """
        Создание нового группового чата
        """
        try:
            name = request.data.get('name')
            description = request.data.get('description', '')
            is_private = request.data.get('is_private', False)
            member_ids = request.data.get('member_ids', [])
            
            if not name:
                return Response(
                    {"detail": "Название чата обязательно"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Создаем новый групповой чат
            group_chat = GroupChat.objects.create(
                name=name,
                description=description,
                is_private=is_private,
                created_by=request.user
            )
            
            # Добавляем создателя в участники
            group_chat.members.add(request.user)
            
            # Добавляем остальных участников
            if member_ids:
                members = User.objects.filter(id__in=member_ids)
                group_chat.members.add(*members)
            
            return Response({
                'status': 'success',
                'message': 'Групповой чат успешно создан',
                'chat_id': group_chat.id,
                'room_name': group_chat.get_room_name()
            })
            
        except Exception as e:
            logger.error(f"Ошибка при создании группового чата: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при создании группового чата"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GroupChatDetailAPI(APIView):
    """
    API для управления конкретным групповым чатом
    """
    
    @method_decorator(check_auth_tokens_api)
    def get(self, request, chat_id):
        """
        Получение информации о групповом чате
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь участником чата
            if not group_chat.members.filter(id=request.user.id).exists():
                return Response(
                    {"detail": "У вас нет доступа к этому чату"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Получаем информацию о чате
            members = group_chat.members.all()
            last_message = group_chat.messages.order_by('-timestamp').first()
            
            # Формируем ответ
            members_data = []
            for member in members:
                members_data.append({
                    'id': member.id,
                    'username': member.username,
                    'first_name': member.first_name,
                    'last_name': member.last_name,
                    'avatar': member.avatar.url if member.avatar else None,
                    'is_creator': member.id == group_chat.created_by.id
                })
            
            return Response({
                'id': group_chat.id,
                'name': group_chat.name,
                'description': group_chat.description,
                'is_private': group_chat.is_private,
                'avatar': group_chat.avatar.url if group_chat.avatar else None,
                'room_name': f"group_{group_chat.id}",
                'created_by': {
                    'id': group_chat.created_by.id,
                    'username': group_chat.created_by.username,
                    'first_name': group_chat.created_by.first_name,
                    'last_name': group_chat.created_by.last_name,
                },
                'created_at': group_chat.created_at.isoformat(),
                'members': members_data,
                'last_message': last_message.message if last_message else None,
                'last_message_time': last_message.timestamp.isoformat() if last_message else None
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка при получении информации о групповом чате: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении информации о чате"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @method_decorator(check_auth_tokens_api)
    def put(self, request, chat_id):
        """
        Обновление информации о групповом чате
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь создателем чата
            if group_chat.created_by != request.user:
                return Response(
                    {"detail": "Только создатель чата может его редактировать"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Обновляем информацию
            name = request.data.get('name')
            description = request.data.get('description')
            is_private = request.data.get('is_private')
            
            if name:
                group_chat.name = name
            if description is not None:
                group_chat.description = description
            if is_private is not None:
                group_chat.is_private = is_private
            
            group_chat.save()
            
            return Response({
                'status': 'success',
                'message': 'Информация о чате успешно обновлена'
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о групповом чате: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при обновлении информации о чате"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @method_decorator(check_auth_tokens_api)
    def delete(self, request, chat_id):
        """
        Удаление группового чата
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь создателем чата
            if group_chat.created_by != request.user:
                return Response(
                    {"detail": "Только создатель чата может его удалить"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            group_chat.delete()
            
            return Response({
                'status': 'success',
                'message': 'Чат успешно удален'
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении группового чата: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при удалении чата"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GroupChatMembersAPI(APIView):
    """
    API для управления участниками группового чата
    """
    
    @method_decorator(check_auth_tokens_api)
    def get(self, request, chat_id):
        """
        Получение списка участников группового чата
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь участником чата
            if not group_chat.members.filter(id=request.user.id).exists():
                return Response(
                    {"detail": "У вас нет доступа к этому чату"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Получаем участников чата
            members = group_chat.members.all()
            
            # Формируем ответ
            members_data = []
            for member in members:
                members_data.append({
                    'id': member.id,
                    'username': member.username,
                    'first_name': member.first_name,
                    'last_name': member.last_name,
                    'avatar': member.avatar.url if member.avatar else None,
                    'is_creator': member.id == group_chat.created_by.id
                })
            
            return Response({
                'members': members_data
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка при получении списка участников группового чата: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при получении списка участников"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @method_decorator(check_auth_tokens_api)
    def post(self, request, chat_id):
        """
        Добавление участников в групповой чат
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь создателем чата
            if group_chat.created_by != request.user:
                return Response(
                    {"detail": "Только создатель чата может добавлять участников"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            member_ids = request.data.get('member_ids', [])
            if not member_ids:
                return Response(
                    {"detail": "Необходимо указать ID участников"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Добавляем участников
            members = User.objects.filter(id__in=member_ids)
            group_chat.members.add(*members)
            
            return Response({
                'status': 'success',
                'message': 'Участники успешно добавлены',
                'added_count': len(member_ids)
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка при добавлении участников в групповой чат: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при добавлении участников"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @method_decorator(check_auth_tokens_api)
    def delete(self, request, chat_id):
        """
        Удаление участников из группового чата
        """
        try:
            group_chat = GroupChat.objects.get(id=chat_id)
            
            # Проверяем, является ли пользователь создателем чата
            if group_chat.created_by != request.user:
                return Response(
                    {"detail": "Только создатель чата может удалять участников"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            data = json.loads(request.body)
            member_ids = data.get('member_ids', [])
            
            if not member_ids:
                return Response(
                    {"detail": "Необходимо указать ID участников"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем, что пользователь не пытается удалить себя (создателя)
            if request.user.id in member_ids:
                return Response(
                    {"detail": "Вы не можете удалить создателя чата"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Удаляем участников
            members = User.objects.filter(id__in=member_ids)
            group_chat.members.remove(*members)
            
            return Response({
                'status': 'success',
                'message': 'Участники успешно удалены',
                'removed_count': len(member_ids)
            })
            
        except GroupChat.DoesNotExist:
            return Response(
                {"detail": "Чат не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except json.JSONDecodeError:
            return Response(
                {"detail": "Неверный формат запроса"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении участников из группового чата: {str(e)}")
            return Response(
                {"detail": "Произошла ошибка при удалении участников"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 