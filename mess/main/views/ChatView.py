from django.shortcuts import render
from django.views import View
from ..decorators import check_auth_tokens
from django.utils.decorators import method_decorator
from ..models import User, ChatMessage
from django.db.models import Q, Max, F, Value, CharField
from django.db.models.functions import Concat
import logging
import re

logger = logging.getLogger(__name__)

class ChatRoomView(View):
    """
    Представление для комнаты чата
    """
    
    @method_decorator(check_auth_tokens)
    def get(self, request, room_name):
        """
        Отображение страницы чата
        """
        context = {
            'room_name': room_name,
            'user': request.user,
            'is_direct_chat': False,
            'chat_title': room_name.replace('_', ' ').capitalize()
        }
        
        # Проверяем, является ли это личным чатом
        direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
        if direct_chat_match:
            context['is_direct_chat'] = True
            
            # Получаем ID пользователей
            user_id1 = int(direct_chat_match.group(1))
            user_id2 = int(direct_chat_match.group(2))
            
            # Определяем собеседника
            other_user_id = user_id1 if request.user.id == user_id2 else user_id2
            
            try:
                other_user = User.objects.get(id=other_user_id)
                context['other_user'] = other_user
                context['chat_title'] = f"Чат с {other_user.first_name} {other_user.last_name}"
            except User.DoesNotExist:
                logger.warning(f"Пользователь с ID {other_user_id} не найден")
        
        # Получаем последние сообщения из чата (например, 20 последних)
        recent_messages = ChatMessage.objects.filter(room_name=room_name).order_by('-timestamp')[:20]
        
        # Если есть сообщения, передаем их в контекст
        if recent_messages.exists():
            context['has_previous_messages'] = True
            context['messages_count'] = ChatMessage.objects.filter(room_name=room_name).count()
        else:
            context['has_previous_messages'] = False
            context['messages_count'] = 0
        
        logger.info(f"Просмотр комнаты чата {room_name} пользователем {request.user.username}")
        return render(request, 'chat.html', context)

class ChatRoomListView(View):
    """
    Представление для списка доступных комнат чата
    """
    
    @method_decorator(check_auth_tokens)
    def get(self, request):
        """
        Отображение страницы со списком доступных комнат
        """
        logger.info(f"Просмотр списка комнат чата пользователем {request.user.username}")
        
        # Общие комнаты чата
        public_rooms = [
            {'id': 'general', 'name': 'Общий чат', 'type': 'public'},
            {'id': 'support', 'name': 'Техподдержка', 'type': 'public'},
            {'id': 'random', 'name': 'Случайные темы', 'type': 'public'}
        ]
        
        # Находим личные чаты пользователя
        direct_chats = []
        
        # Два способа получения личных чатов:
        # 1. Чаты, в которых пользователь писал сообщения
        # 2. Чаты, созданные при переходе с профилей других пользователей
        
        # Шаблон для личных чатов
        direct_chat_pattern = r'^direct_\d+_\d+$'
        
        # Получаем все уникальные комнаты, в которых участвовал пользователь
        user_chat_rooms = ChatMessage.objects.filter(
            Q(user=request.user) | Q(room_name__contains=f'_{request.user.id}_') | Q(room_name__contains=f'_direct_{request.user.id}')
        ).values_list('room_name', flat=True).distinct()
        
        # Фильтруем только личные чаты
        direct_chat_rooms = [room for room in user_chat_rooms if re.match(direct_chat_pattern, room)]
        
        # Добавляем еще те чаты, где пользователь может быть участником, но еще не писал сообщения
        direct_chat_pattern_1 = f'direct_{request.user.id}_\\d+'
        direct_chat_pattern_2 = f'direct_\\d+_{request.user.id}'
        
        additional_chats = ChatMessage.objects.filter(
            Q(room_name__regex=direct_chat_pattern_1) | Q(room_name__regex=direct_chat_pattern_2)
        ).values_list('room_name', flat=True).distinct()
        
        # Объединяем списки комнат и удаляем дубликаты
        all_chat_rooms = list(set(direct_chat_rooms) | set(additional_chats))
        
        # Получаем информацию о других участниках чатов
        for room_name in all_chat_rooms:
            direct_chat_match = re.match(r'^direct_(\d+)_(\d+)$', room_name)
            if direct_chat_match:
                user_id1 = int(direct_chat_match.group(1))
                user_id2 = int(direct_chat_match.group(2))
                
                # Определяем собеседника
                other_user_id = user_id1 if request.user.id == user_id2 else user_id2
                
                try:
                    other_user = User.objects.get(id=other_user_id)
                    
                    # Получаем последнее сообщение в чате
                    last_message = ChatMessage.objects.filter(
                        room_name=room_name
                    ).order_by('-timestamp').first()
                    
                    direct_chats.append({
                        'id': room_name,
                        'name': f"{other_user.first_name} {other_user.last_name}",
                        'user': other_user,
                        'type': 'direct',
                        'last_message': last_message.message if last_message else '',
                        'last_message_time': last_message.timestamp if last_message else None
                    })
                except User.DoesNotExist:
                    logger.warning(f"Пользователь с ID {other_user_id} не найден")
        
        # Сортируем личные чаты по времени последнего сообщения (новые сверху)
        direct_chats.sort(key=lambda x: x['last_message_time'] if x['last_message_time'] else 0, reverse=True)
        
        return render(request, 'chat_rooms.html', {
            'public_rooms': public_rooms,
            'direct_chats': direct_chats,
            'user': request.user
        }) 