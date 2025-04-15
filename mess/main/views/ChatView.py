from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from main.models import ChatRoom, Message, User
from main.serializers import MessageSerializer, ChatRoomSerializer
from main.decorators import check_auth_tokens, check_auth_tokens_api
from django.utils.decorators import method_decorator

@method_decorator(check_auth_tokens, name='dispatch')
class ChatListView(TemplateView):
    template_name = 'chat/chat_list.html'

@method_decorator(check_auth_tokens, name='dispatch')
class ChatRoomView(TemplateView):
    template_name = 'chat/chat_room.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room_id = kwargs.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Проверяем, является ли пользователь участником чата
        if self.request.user not in room.participants.all():
            # Если это личный чат, проверяем права доступа
            context['error'] = "У вас нет доступа к этому чату"
        
        context['room'] = room
        return context

class ChatRoomAPIView(APIView):
    @method_decorator(check_auth_tokens)
    def get(self, request):
        # Получаем все чаты пользователя
        rooms = ChatRoom.objects.filter(participants=request.user)
        serializer = ChatRoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    @method_decorator(check_auth_tokens_api)
    def post(self, request):
        # Создаем новый чат
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({"error": "Необходимо указать ID пользователя"}, status=400)
            
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)
            
        # Проверяем, существует ли уже чат между этими пользователями
        existing_chat = ChatRoom.objects.filter(participants=request.user).filter(participants=other_user)
        
        if existing_chat.exists() and existing_chat.count() == 1:
            serializer = ChatRoomSerializer(existing_chat.first())
            return Response(serializer.data)
            
        # Создаем новый чат
        chat = ChatRoom.objects.create()
        chat.participants.add(request.user, other_user)
        serializer = ChatRoomSerializer(chat)
        return Response(serializer.data)

class ChatMessagesAPIView(APIView):
    @method_decorator(check_auth_tokens_api)
    def get(self, request, room_id):
        # Проверяем существование комнаты
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Проверяем, является ли пользователь участником чата
        if request.user not in room.participants.all():
            return Response({"error": "У вас нет доступа к этому чату"}, status=403)
            
        # Получаем сообщения
        messages = Message.objects.filter(room=room).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @method_decorator(check_auth_tokens_api)
    def post(self, request, room_id):
        # Проверяем существование комнаты
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Проверяем, является ли пользователь участником чата
        if request.user not in room.participants.all():
            return Response({"error": "У вас нет доступа к этому чату"}, status=403)
            
        # Создаем новое сообщение
        content = request.data.get('message')
        if not content:
            return Response({"error": "Сообщение не может быть пустым"}, status=400)
            
        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=content
        )
        
        serializer = MessageSerializer(message)
        return Response(serializer.data)
