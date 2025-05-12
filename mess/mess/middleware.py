import os
from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve

class StaticFilesMiddleware:
    """
    Middleware для обслуживания статических файлов даже в режиме DEBUG=False
    Это необходимо для корректного отображения страниц ошибок (404, 500, 403)
    с подключенными стилями CSS
    
    Примечание: В production-среде статические файлы должны обслуживаться веб-сервером,
    а не Django. Эта middleware создана только для удобства разработки и тестирования.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Если ответ - ошибка 404, 500 или 403, и запрос был для статического файла
        if (response.status_code in [404, 500, 403] and 
            request.path.startswith(settings.STATIC_URL) and
            not settings.DEBUG):
            
            # Попытка найти и обслужить статический файл
            path = request.path[len(settings.STATIC_URL):]
            
            # Проверяем в STATIC_ROOT
            if settings.STATIC_ROOT:
                full_path = os.path.join(settings.STATIC_ROOT, path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    return serve(request, path, document_root=settings.STATIC_ROOT)
            
            # Проверяем в STATICFILES_DIRS
            for static_dir in settings.STATICFILES_DIRS:
                full_path = os.path.join(static_dir, path)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    return serve(request, path, document_root=static_dir)
        
        return response 