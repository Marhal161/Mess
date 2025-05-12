from django.shortcuts import render

def custom_page_not_found(request, exception, template_name='404.html'):
    """
    Обработчик для ошибки 404 (Страница не найдена)
    Работает как при DEBUG=True, так и при DEBUG=False
    """
    return render(request, template_name, status=404)

def custom_server_error(request, template_name='500.html'):
    """
    Обработчик для ошибки 500 (Внутренняя ошибка сервера)
    Работает как при DEBUG=True, так и при DEBUG=False
    """
    return render(request, template_name, status=500)

def custom_permission_denied(request, exception, template_name='403.html'):
    """
    Обработчик для ошибки 403 (Доступ запрещен)
    Работает как при DEBUG=True, так и при DEBUG=False
    """
    return render(request, template_name, status=403)

def force_custom_404(request):
    """
    Принудительно вызывает отображение пользовательской страницы 404
    Используется для тестирования страницы ошибки
    """
    return custom_page_not_found(request, None)

def force_custom_500(request):
    """
    Принудительно вызывает отображение пользовательской страницы 500
    Используется для тестирования страницы ошибки
    """
    return custom_server_error(request)

def force_custom_403(request):
    """
    Принудительно вызывает отображение пользовательской страницы 403
    Используется для тестирования страницы ошибки
    """
    return custom_permission_denied(request, None) 