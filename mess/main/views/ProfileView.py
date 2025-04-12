from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from main.models import Interest
from django.db import transaction
import logging
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from main.decorators import check_auth_tokens, check_auth_tokens_api

User = get_user_model()
logger = logging.getLogger(__name__)

class ProfileTemplateView(TemplateView):
    """Представление для рендеринга шаблона профиля"""
    template_name = 'profile/profile.html'
    
    def get(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')
        
        logger.info(f"ProfileTemplateView: Проверка токенов при загрузке страницы профиля")
        logger.info(f"ProfileTemplateView: Access token существует: {bool(access_token)}")
        logger.info(f"ProfileTemplateView: Refresh token существует: {bool(refresh_token)}")
        
        # Если токенов нет, перенаправляем на страницу входа
        if not refresh_token:
            logger.debug("ProfileTemplateView: Refresh токен отсутствует, перенаправляем на страницу входа")
            from django.shortcuts import redirect
            return redirect('login_page')
        
        # Проверим токены с помощью встроенных методов
        try:
            from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
            from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
            
            # Если доступа нет, пробуем использовать refresh token
            if not access_token:
                logger.debug("ProfileTemplateView: Access токен отсутствует, создаем новый")
                try:
                    refresh = RefreshToken(refresh_token)
                    access_token = str(refresh.access_token)
                    
                    # Получаем пользователя
                    user_id = refresh['user_id']
                    request.user = User.objects.get(id=user_id)
                    
                    logger.info(f"ProfileTemplateView: Успешно создан новый access token для пользователя {user_id}")
                    
                    response = super().get(request, *args, **kwargs)
                    response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=86400)  # 1 день
                    return response
                except (TokenError, InvalidToken) as e:
                    logger.error(f"ProfileTemplateView: Ошибка при создании токена: {str(e)}")
                    return redirect('login_page')
            
            # Если access_token есть, пробуем его использовать
            try:
                token = AccessToken(access_token)
                user_id = token['user_id']
                request.user = User.objects.get(id=user_id)
                logger.info(f"ProfileTemplateView: Использован существующий access token для пользователя {user_id}")
            except (TokenError, InvalidToken) as e:
                logger.debug(f"ProfileTemplateView: Access токен недействителен: {str(e)}, пробуем обновить")
                try:
                    refresh = RefreshToken(refresh_token)
                    new_access_token = str(refresh.access_token)
                    
                    user_id = refresh['user_id']
                    request.user = User.objects.get(id=user_id)
                    
                    logger.info(f"ProfileTemplateView: Успешно обновлен access токен для пользователя {user_id}")
                    
                    response = super().get(request, *args, **kwargs)
                    response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax', max_age=86400)  # 1 день
                    logger.info("ProfileTemplateView: Установлен новый access_token в куки")
                    return response
                except (TokenError, InvalidToken) as e:
                    logger.error(f"ProfileTemplateView: Ошибка при обновлении токена: {str(e)}")
                    return redirect('login_page')
            
            return super().get(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"ProfileTemplateView: Неожиданная ошибка при проверке токена: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return redirect('login_page')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ProfileView(APIView):
    """API представление для работы с профилем пользователя"""
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    @check_auth_tokens_api
    def get(self, request, user_id=None):
        """Получение профиля пользователя"""
        try:
            # Если user_id не указан, возвращаем профиль текущего пользователя
            if user_id is None:
                user = request.user
            else:
                user = get_object_or_404(User, id=user_id)
                
            # Подготавливаем данные профиля
            profile_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'bio': user.bio,
                'gender': user.gender,
                'kurs': user.kurs,
                'avatar': user.avatar.url if user.avatar else None,
                'interests': [{'id': interest.id, 'name': interest.name} for interest in user.interests.all()]
            }
            
            return Response(profile_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {str(e)}")
            return Response(
                {"detail": "Ошибка при получении профиля"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @check_auth_tokens_api
    def put(self, request):
        """Обновление профиля пользователя"""
        try:
            user = request.user
            data = request.data
            
            with transaction.atomic():
                # Обновляем основные поля
                if 'first_name' in data:
                    user.first_name = data['first_name']
                if 'last_name' in data:
                    user.last_name = data['last_name']
                if 'email' in data:
                    # Проверка уникальности email
                    if User.objects.filter(email=data['email']).exclude(id=user.id).exists():
                        return Response(
                            {"detail": "Email уже используется другим пользователем"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    user.email = data['email']
                if 'phone' in data:
                    user.phone = data['phone']
                if 'bio' in data:
                    user.bio = data['bio']
                if 'gender' in data:
                    user.gender = data['gender']
                if 'kurs' in data:
                    user.kurs = data['kurs']
                
                # Обработка фотографии
                if 'avatar' in request.FILES:
                    # Если есть старый аватар, удаляем его
                    if user.avatar:
                        if os.path.isfile(os.path.join(settings.MEDIA_ROOT, user.avatar.name)):
                            os.remove(os.path.join(settings.MEDIA_ROOT, user.avatar.name))
                    
                    # Сохраняем новый аватар
                    avatar_file = request.FILES['avatar']
                    
                    # Создаем путь для сохранения файла: profiles/username/filename
                    # Очистка имени пользователя от спецсимволов и приведение к нижнему регистру
                    username = ''.join(c for c in user.username if c.isalnum() or c == '_').lower()
                    profile_dir = os.path.join('profiles', username)
                    
                    # Создаем директорию, если она не существует
                    full_profile_dir = os.path.join(settings.MEDIA_ROOT, profile_dir)
                    os.makedirs(full_profile_dir, exist_ok=True)
                    
                    # Сохраняем файл
                    path = default_storage.save(
                        os.path.join(profile_dir, avatar_file.name),
                        ContentFile(avatar_file.read())
                    )
                    user.avatar = path
                
                # Обработка интересов
                if 'interests' in data:
                    # Удаляем все связи с интересами
                    user.interests.clear()
                    
                    # Добавляем новые интересы
                    interests_ids = data.getlist('interests') if hasattr(data, 'getlist') else data.get('interests', [])
                    interests = Interest.objects.filter(id__in=interests_ids)
                    user.interests.add(*interests)
                
                user.save()
                
                return Response(
                    {"detail": "Профиль успешно обновлен"},
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении профиля: {str(e)}")
            return Response(
                {"detail": f"Ошибка при обновлении профиля: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @check_auth_tokens_api
    def delete(self, request):
        """Удаление аккаунта пользователя"""
        try:
            user = request.user
            
            # Логика деактивации пользователя вместо полного удаления
            user.is_active = False
            user.save()
            
            return Response(
                {"detail": "Аккаунт деактивирован"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Ошибка при удалении аккаунта: {str(e)}")
            return Response(
                {"detail": "Ошибка при удалении аккаунта"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class ChangePasswordView(APIView):
    """API представление для смены пароля"""
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    @check_auth_tokens_api
    def post(self, request):
        try:
            user = request.user
            data = request.data
            
            # Проверка текущего пароля
            if not user.check_password(data.get('current_password')):
                return Response(
                    {"detail": "Неверный текущий пароль"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверка нового пароля
            new_password = data.get('new_password')
            if len(new_password) < 8:
                return Response(
                    {"detail": "Пароль должен содержать не менее 8 символов"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Установка нового пароля
            user.set_password(new_password)
            user.save()
            
            return Response(
                {"detail": "Пароль успешно изменен"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Ошибка при смене пароля: {str(e)}")
            return Response(
                {"detail": "Ошибка при смене пароля"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


