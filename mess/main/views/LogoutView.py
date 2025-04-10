from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import logout

class LogoutView(APIView):
    """
    Представление для выхода пользователя из системы
    """
    
    def post(self, request):
        # Выходим пользователя из системы
        logout(request)
        
        # Создаем ответ
        response = Response({"success": True, "message": "Выход выполнен успешно"}, status=status.HTTP_200_OK)
        
        # Удаляем JWT токены из кук
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response