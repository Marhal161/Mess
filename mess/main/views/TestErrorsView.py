from django.shortcuts import render
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.views import View
from .ErrorHandlerView import force_custom_404, force_custom_500, force_custom_403

class TestErrorsView(View):
    """
    Представление для тестирования страниц ошибок
    """
    
    def get(self, request, error_type=None):
        """
        Вызывает ошибку указанного типа для тестирования страниц ошибок
        """
        if error_type == '404':
            # Вызов 404 ошибки
            return force_custom_404(request)
            
        elif error_type == '500':
            # Вызов 500 ошибки
            return force_custom_500(request)
            
        elif error_type == '403':
            # Вызов 403 ошибки
            return force_custom_403(request)
            
        else:
            # Если указан неизвестный тип ошибки, показываем тестовую страницу
            return render(request, 'test_errors.html', {
                'error_types': ['404', '500', '403']
            }) 