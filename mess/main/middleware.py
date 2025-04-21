import logging
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, TokenError
import traceback

logger = logging.getLogger(__name__)
User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_str):
    """
    Получение пользователя из JWT токена
    """
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return User.objects.get(id=user_id)
    except (TokenError, User.DoesNotExist) as e:
        logger.error(f"Ошибка при получении пользователя из токена: {str(e)}")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке токена: {str(e)}")
        logger.error(traceback.format_exc())
        return AnonymousUser()

class JwtCookieMiddleware(BaseMiddleware):
    """
    Middleware для аутентификации WebSocket соединений через JWT токены в cookie
    """
    
    async def __call__(self, scope, receive, send):
        # Получаем cookies из scope
        cookies = {}
        headers = dict(scope.get('headers', []))
        cookie_header = headers.get(b'cookie', b'').decode()
        
        # Парсим cookies
        if cookie_header:
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
        
        # Пытаемся получить access_token
        access_token = cookies.get('access_token')
        
        if access_token:
            logger.info("JwtCookieMiddleware: Найден access_token в cookie")
            scope['user'] = await get_user_from_token(access_token)
        else:
            logger.warning("JwtCookieMiddleware: Токен не найден в cookie")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send) 