import logging
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

def check_auth_tokens(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

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
                
                response = view_func(request, *args, **kwargs)
                response.set_cookie('access_token', new_access_token, httponly=True)
                return response
                
            except (TokenError, InvalidToken) as refresh_error:
                logger.debug(f"Refresh токен невалиден: {str(refresh_error)}")
                return redirect('login_page')
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке токена: {str(e)}")
            return redirect('login_page')

    return _wrapped_view