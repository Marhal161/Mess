from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation, get_user_model, login
from ..serializers import RegisterSerializer
from ..models import Interest
from django.middleware.csrf import get_token
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

User = get_user_model()

class RegisterView(APIView):
    """
    Представление для регистрации нового пользователя
    """
    
    def post(self, request):
        try:
            data = request.data
            
            # Проверка основных обязательных полей
            required_fields = ['email', 'password', 'first_name', 'last_name', 'phone']
            for field in required_fields:
                if field not in data or not data[field]:
                    return Response({
                        'success': False,
                        'errors': f'Поле {field} обязательно для заполнения'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверка существования email
            if User.objects.filter(email=data['email']).exists():
                return Response({
                    'success': False,
                    'errors': 'Пользователь с таким email уже существует'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Создание пользователя
            user = User(
                username=data['email'],  # Используем email как username
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data['phone'],
                is_active=True
            )
            
            # Установка дополнительных полей, если они предоставлены
            if 'bio' in data and data['bio']:
                user.bio = data['bio']
            
            if 'gender' in data and data['gender']:
                user.gender = data['gender']
            
            if 'kurs' in data and data['kurs']:
                user.kurs = data['kurs']
            
            # Установка пароля
            user.set_password(data['password'])
            user.save()
            
            # Добавление интересов, если они указаны
            if 'interests' in data and data['interests']:
                interests = Interest.objects.filter(id__in=data['interests'])
                user.interests.add(*interests)
            
            # Автоматический вход пользователя
            login(request, user)
            
            # Создаем JWT токены
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            # Получаем CSRF токен
            csrf_token = get_token(request)
            
            response_data = {
                'success': True,
                'message': 'Регистрация успешно завершена',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': access_token
                },
                'csrf_token': csrf_token
            }
            
            # Создаем ответ
            response = Response(response_data, status=status.HTTP_201_CREATED)
            
            # Устанавливаем куки
            response.set_cookie('access_token', access_token, httponly=True)
            response.set_cookie('refresh_token', str(refresh), httponly=True)
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации: {e}")
            return Response({
                'success': False,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)