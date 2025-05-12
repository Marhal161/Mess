"""
URL configuration for mess project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler500, handler403
from main.views.ErrorHandlerView import custom_page_not_found, custom_server_error, custom_permission_denied

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include('main.urls')),
]

# Обработчики ошибок
handler404 = custom_page_not_found
handler500 = custom_server_error
handler403 = custom_permission_denied

# Обслуживание статических и медиа-файлов
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# Обновленная конфигурация для обслуживания статических файлов, которая будет работать 
# независимо от значения DEBUG
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT if settings.STATIC_ROOT else settings.STATICFILES_DIRS[0])