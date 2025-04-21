from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import ChatMessage, User
from ..decorators import check_auth_tokens
from django.utils.decorators import method_decorator
import logging
import re

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
            
            # Сериализуем сообщения
            serialized_messages = []
            for msg in messages:
                serialized_messages.append({
                    'id': msg.id,
                    'message': msg.message,
                    'timestamp': msg.timestamp.isoformat(),
                    'user': {
                        'id': msg.user.id,
                        'username': msg.user.username,
                        'first_name': msg.user.first_name,
                        'last_name': msg.user.last_name
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