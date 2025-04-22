from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from ..serializers.LoginSerializer import LogSerializer
from django.contrib.auth import authenticate, login, get_user_model
from django.middleware.csrf import get_token
from django.http import JsonResponse
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class LoginView(APIView):
    """
    Представление для входа пользователя
    """
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        logger.info(f"Попытка входа для пользователя с email: {email}")
        
        if not email or not password:
            return Response(
                {"detail": "Необходимо указать email и пароль"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ищем пользователя по email
        try:
            user = User.objects.get(email=email)
            logger.info(f"Найден пользователь с email {email}: {user.username}")
            
            # Проверяем активность аккаунта
            if not user.is_active:
                logger.warning(f"Попытка входа в деактивированный аккаунт: {user.username}")
                return Response(
                    {"detail": "Аккаунт отключен. Обратитесь к администратору."},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Проверяем пароль
            if user.check_password(password):
                logger.info(f"Пароль верный для пользователя {user.username}")
                
                # Вход пользователя
                login(request, user)
                
                # Создаем токены
                refresh = RefreshToken.for_user(user)
                access = str(refresh.access_token)
                
                # Получаем CSRF токен
                csrf_token = get_token(request)
                
                response_data = {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name
                    },
                    "tokens": {
                        "refresh": str(refresh),
                        "access": access
                    },
                    "csrf_token": csrf_token
                }
                
                # Создаем ответ
                response = Response(response_data, status=status.HTTP_200_OK)
                
                # Устанавливаем куки
                response.set_cookie('access_token', access, httponly=True, path='/')
                response.set_cookie('refresh_token', str(refresh), httponly=True, path='/')
                
                logger.info(f"Пользователь {user.username} успешно вошел в систему")
                return response
            else:
                logger.warning(f"Неверный пароль для пользователя с email {email}")
                return Response(
                    {"detail": "Неверный пароль"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            logger.warning(f"Пользователь с email {email} не найден")
            return Response(
                {"detail": "Пользователь с таким email не найден"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Ошибка при входе пользователя {email}: {str(e)}")
            return Response(
                {"detail": f"Ошибка при входе: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )