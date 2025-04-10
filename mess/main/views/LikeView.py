from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from main.models import Like, User
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class LikeUserView(APIView):
    # Используем несколько систем аутентификации
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        logger.info(f"Получен запрос на лайк пользователя с ID: {user_id}")
        logger.info(f"Текущий пользователь: {request.user}, ID: {request.user.id}")
        logger.info(f"Метод аутентификации: {request.auth}")
        logger.info(f"Заголовки запроса: {request.headers}")
        
        try:
            to_user = User.objects.get(id=user_id)
            logger.info(f"Найден пользователь для лайка: {to_user.username}")
            
            # Проверяем, не пытается ли пользователь лайкнуть самого себя
            if request.user.id == to_user.id:
                logger.warning(f"Пользователь {request.user.username} пытается лайкнуть сам себя")
                return Response(
                    {"detail": "Вы не можете лайкнуть себя"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверяем, существует ли уже лайк
            existing_like = Like.objects.filter(from_user=request.user, to_user=to_user).exists()
            if existing_like:
                logger.info(f"Лайк от пользователя {request.user.username} к {to_user.username} уже существует")
                return Response(
                    {"detail": f"Вы уже лайкнули пользователя {to_user.username}"},
                    status=status.HTTP_200_OK
                )
            
            # Создаем лайк
            logger.info(f"Создаем новый лайк от {request.user.username} к {to_user.username}")
            like = Like.objects.create(
                from_user=request.user,
                to_user=to_user
            )
            logger.info(f"Лайк успешно создан: {like}")
            
            return Response(
                {"detail": f"Вы успешно лайкнули пользователя {to_user.username}"},
                status=status.HTTP_201_CREATED
            )
                
        except User.DoesNotExist:
            logger.error(f"Пользователь с ID {user_id} не найден")
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except IntegrityError as e:
            logger.error(f"Ошибка целостности при создании лайка: {str(e)}")
            return Response(
                {"detail": "Вы уже лайкнули этого пользователя"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании лайка: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 