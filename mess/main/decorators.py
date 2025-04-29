import logging
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
import traceback

logger = logging.getLogger(__name__)

# Декоратор для веб-представлений (с перенаправлением)
def check_auth_tokens(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        logger.info("check_auth_tokens: Проверка токенов для веб-представления")
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        logger.info(f"check_auth_tokens: Access token существует: {bool(access_token)}")
        logger.info(f"check_auth_tokens: Refresh token существует: {bool(refresh_token)}")

        if not refresh_token:
            logger.debug("Refresh токен отсутствует")
            return redirect('login_page')

        if not access_token:
            logger.debug("Access токен отсутствует, пробуем создать новый из refresh токена")
            try:
                refresh = RefreshToken(refresh_token)
                access_token = str(refresh.access_token)
                
                # Получаем пользователя из refresh токена
                user_id = refresh['user_id']
                User = get_user_model()
                request.user = User.objects.get(id=user_id)
                
                logger.info(f"check_auth_tokens: Создан новый access token для пользователя {user_id}")
                
                response = view_func(request, *args, **kwargs)
                response.set_cookie('access_token', access_token, httponly=True)
                return response
            except (TokenError, InvalidToken) as refresh_error:
                logger.debug(f"Refresh токен невалиден: {str(refresh_error)}")
                return redirect('login_page')

        try:
            # Получаем пользователя из токена
            token = AccessToken(access_token)
            user_id = token['user_id']
            User = get_user_model()
            request.user = User.objects.get(id=user_id)
            logger.info(f"check_auth_tokens: Использован существующий access token для пользователя {user_id}")
            return view_func(request, *args, **kwargs)
            
        except (TokenError, InvalidToken) as e:
            logger.debug(f"Access токен невалиден или устарел: {str(e)}")
            
            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)
                
                # Получаем пользователя из refresh токена
                user_id = refresh['user_id']
                User = get_user_model()
                request.user = User.objects.get(id=user_id)
                
                logger.info(f"check_auth_tokens: Обновлен access token для пользователя {user_id}")
                
                response = view_func(request, *args, **kwargs)
                response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax', max_age=86400)  # 1 день
                return response
                
            except (TokenError, InvalidToken) as refresh_error:
                logger.debug(f"Refresh токен невалиден: {str(refresh_error)}")
                return redirect('login_page')
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке токена: {str(e)}")
            logger.error(traceback.format_exc())
            return redirect('login_page')

    return _wrapped_view

# Декоратор для API-представлений (с возвратом JSON)
def check_auth_tokens_api(view_func):
    @wraps(view_func)
    def _wrapped_view(*args, **kwargs):
        # Определяем request из аргументов или kwargs
        if len(args) > 0 and hasattr(args[0], 'COOKIES') and hasattr(args[0], 'headers'):
            # Случай, когда первый аргумент уже является объектом Request
            request = args[0]
            logger.info("check_auth_tokens_api: Первый аргумент уже является Request")
        elif len(args) > 1:
            # Обычный случай для методов класса: (self, request, ...)
            request = args[1]
        elif 'request' in kwargs:
            # Случай когда request передается через kwargs
            request = kwargs['request']
        elif len(args) > 0 and hasattr(args[0], 'request'):
            # Случай для APIView, где request доступен как self.request
            request = args[0].request
        else:
            # Если не удалось получить request, возвращаем ошибку
            logger.error("check_auth_tokens_api: Не удалось получить объект request")
            logger.error(f"args: {args}, kwargs: {kwargs}")
            return Response(
                {"detail": "Ошибка сервера: не удалось получить объект запроса"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info("check_auth_tokens_api: Проверка токенов для API")
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')
        
        auth_header = request.headers.get('Authorization', '')
        
        logger.info(f"check_auth_tokens_api: Access token в куках: {bool(access_token)}")
        logger.info(f"check_auth_tokens_api: Refresh token в куках: {bool(refresh_token)}")
        logger.info(f"check_auth_tokens_api: Authorization header: {auth_header}")

        # Сначала проверяем заголовок Authorization
        if auth_header.startswith('Bearer '):
            token_from_header = auth_header.split(' ')[1]
            logger.info("check_auth_tokens_api: Найден Bearer токен в заголовке")
            try:
                token = AccessToken(token_from_header)
                user_id = token['user_id']
                User = get_user_model()
                request.user = User.objects.get(id=user_id)
                logger.info(f"check_auth_tokens_api: Использован токен из заголовка для пользователя {user_id}")
                
                # Запишем токен в куки для дальнейшего использования
                response = view_func(*args, **kwargs)
                if not access_token:
                    logger.info("check_auth_tokens_api: Добавляем токен из заголовка в куки")
                    response.set_cookie('access_token', token_from_header, httponly=True, samesite='Lax', max_age=86400)
                return response
            except (TokenError, InvalidToken) as e:
                # Если токен в заголовке недействителен, продолжаем проверять куки
                logger.debug(f"check_auth_tokens_api: Токен в заголовке невалиден: {str(e)}")
                # продолжаем проверку с куками
            except Exception as e:
                logger.error(f"check_auth_tokens_api: Ошибка при проверке токена из заголовка: {str(e)}")
                logger.error(traceback.format_exc())
                
        # Проверка по кукам, если нет валидного токена в заголовке
        if not refresh_token:
            logger.debug("check_auth_tokens_api: Refresh токен отсутствует")
            return Response(
                {"detail": "Требуется аутентификация"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not access_token:
            logger.debug("check_auth_tokens_api: Access токен отсутствует, пробуем создать новый из refresh токена")
            try:
                refresh = RefreshToken(refresh_token)
                access_token = str(refresh.access_token)
                
                # Получаем пользователя из refresh токена
                user_id = refresh['user_id']
                User = get_user_model()
                request.user = User.objects.get(id=user_id)
                
                logger.info(f"check_auth_tokens_api: Создан новый access token для пользователя {user_id}")
                
                response = view_func(*args, **kwargs)
                response.set_cookie('access_token', access_token, httponly=True, samesite='Lax', max_age=86400)  # 1 день
                return response
            except (TokenError, InvalidToken) as refresh_error:
                logger.debug(f"check_auth_tokens_api: Refresh токен невалиден: {str(refresh_error)}")
                return Response(
                    {"detail": "Невалидный токен авторизации"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )

        try:
            # Получаем пользователя из токена
            token = AccessToken(access_token)
            user_id = token['user_id']
            User = get_user_model()
            request.user = User.objects.get(id=user_id)
            logger.info(f"check_auth_tokens_api: Использован существующий access token для пользователя {user_id}")
            return view_func(*args, **kwargs)
            
        except (TokenError, InvalidToken) as e:
            logger.debug(f"check_auth_tokens_api: Access токен невалиден или устарел: {str(e)}")
            
            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)
                
                # Получаем пользователя из refresh токена
                user_id = refresh['user_id']
                User = get_user_model()
                request.user = User.objects.get(id=user_id)
                
                logger.info(f"check_auth_tokens_api: Обновлен access token для пользователя {user_id}")
                
                response = view_func(*args, **kwargs)
                response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax', max_age=86400)  # 1 день
                return response
                
            except (TokenError, InvalidToken) as refresh_error:
                logger.debug(f"check_auth_tokens_api: Refresh токен невалиден: {str(refresh_error)}")
                return Response(
                    {"detail": "Невалидный токен авторизации"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except Exception as e:
            logger.error(f"check_auth_tokens_api: Неожиданная ошибка при проверке токена: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": f"Ошибка аутентификации: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return _wrapped_view