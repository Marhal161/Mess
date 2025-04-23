from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from ..models import ChatReport, User, ChatMessage, Role
from ..decorators import check_auth_tokens
from django.utils.decorators import method_decorator
import logging
import json

logger = logging.getLogger(__name__)

class ModeratorRequiredMixin:
    """
    Mixin для проверки, является ли пользователь модератором
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_page')
        
        # Проверяем, есть ли у пользователя роль Moder
        if not request.user.role.filter(name='Moder').exists():
            return HttpResponseForbidden("У вас нет прав доступа к этой странице")
        
        return super().dispatch(request, *args, **kwargs)

class ModeratorPanelView(ModeratorRequiredMixin, View):
    """
    Главная страница панели модератора
    """
    @method_decorator(check_auth_tokens)
    def get(self, request):
        # Получаем статистику по жалобам
        pending_reports_count = ChatReport.objects.filter(status='pending').count()
        processed_reports_count = ChatReport.objects.filter(status='processed').count()
        rejected_reports_count = ChatReport.objects.filter(status='rejected').count()
        
        # Получаем список последних жалоб
        recent_reports = ChatReport.objects.order_by('-created_at')[:10]
        
        context = {
            'pending_reports_count': pending_reports_count,
            'processed_reports_count': processed_reports_count,
            'rejected_reports_count': rejected_reports_count,
            'recent_reports': recent_reports,
            'user': request.user
        }
        
        return render(request, 'moderator/dashboard.html', context)

class ReportListView(ModeratorRequiredMixin, View):
    """
    Просмотр списка жалоб
    """
    @method_decorator(check_auth_tokens)
    def get(self, request):
        # Получаем параметры фильтрации
        status_filter = request.GET.get('status', 'all')
        
        # Фильтруем жалобы
        reports = ChatReport.objects.all().order_by('-created_at')
        
        if status_filter != 'all':
            reports = reports.filter(status=status_filter)
        
        context = {
            'reports': reports,
            'current_filter': status_filter,
            'user': request.user
        }
        
        return render(request, 'moderator/reports_list.html', context)

class ReportDetailView(ModeratorRequiredMixin, View):
    """
    Детальный просмотр жалобы
    """
    @method_decorator(check_auth_tokens)
    def get(self, request, report_id):
        report = get_object_or_404(ChatReport, id=report_id)
        
        # Получаем информацию о чате
        room_name = report.room_name
        
        # Если это личный чат, получаем информацию о пользователях
        chat_users = []
        if room_name.startswith('direct_'):
            parts = room_name.split('_')
            if len(parts) >= 3:
                user_id1 = int(parts[1])
                user_id2 = int(parts[2])
                try:
                    user1 = User.objects.get(id=user_id1)
                    user2 = User.objects.get(id=user_id2)
                    chat_users = [user1, user2]
                except User.DoesNotExist:
                    pass
        
        # Получаем последние сообщения из чата
        recent_messages = ChatMessage.objects.filter(room_name=room_name).order_by('-timestamp')[:20]
        
        context = {
            'report': report,
            'chat_users': chat_users,
            'recent_messages': recent_messages,
            'room_name': room_name,
            'user': request.user
        }
        
        return render(request, 'moderator/report_detail.html', context)
    
    @method_decorator(check_auth_tokens)
    def post(self, request, report_id):
        report = get_object_or_404(ChatReport, id=report_id)
        
        # Получаем данные из формы
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action in ['process', 'reject']:
            # Обновляем статус жалобы
            report.status = 'processed' if action == 'process' else 'rejected'
            report.moderator_notes = notes
            report.processed_by = request.user
            report.processed_at = timezone.now()
            report.save()
            
            logger.info(f"Жалоба #{report.id} обработана модератором {request.user.username}: {report.status}")
            
            # Если жалоба принята, создаем предупреждение пользователю
            if action == 'process':
                try:
                    # Получаем информацию о комнате чата
                    room_name = report.room_name
                    
                    # Определяем пользователя, на которого была подана жалоба
                    user_id = None
                    if room_name.startswith('direct_'):
                        parts = room_name.split('_')
                        if len(parts) >= 3:
                            # Берем ID обоих пользователей из имени комнаты
                            user_id1 = int(parts[1])
                            user_id2 = int(parts[2])
                            
                            # Пользователь, на которого жалуются - тот, кто не является отправителем жалобы
                            if user_id1 == report.reporter.id:
                                user_id = user_id2
                            else:
                                user_id = user_id1
                    
                    if user_id:
                        from main.models import UserWarning
                        user = User.objects.get(id=user_id)
                        
                        # Создаем предупреждение
                        warning = UserWarning.objects.create(
                            user=user,
                            report=report,
                            moderator=request.user,
                            reason=f"Предупреждение на основании жалобы #{report.id}: {notes}"
                        )
                        
                        # Обновляем флаг предупреждений у пользователя
                        user.has_warnings = True
                        user.save()
                        
                        logger.info(f"Создано предупреждение для пользователя {user.username} на основании жалобы #{report.id}")
                except Exception as e:
                    logger.error(f"Ошибка при создании предупреждения: {str(e)}")
            
            messages.success(request, f"Жалоба успешно {('обработана' if action == 'process' else 'отклонена')}.")
            return redirect('moder_reports_list')
        
        messages.error(request, "Некорректное действие.")
        return redirect('moder_report_detail', report_id=report_id)

class ModerUserManagementView(ModeratorRequiredMixin, View):
    """
    Управление пользователями
    """
    @method_decorator(check_auth_tokens)
    def get(self, request, user_id=None):
        if user_id:
            # Детальный просмотр пользователя
            user_obj = get_object_or_404(User, id=user_id)
            return render(request, 'moderator/user_detail.html', {'user_obj': user_obj, 'user': request.user})
        else:
            # Список пользователей
            search_query = request.GET.get('search', '')
            users = User.objects.all().order_by('-date_joined')
            
            if search_query:
                users = users.filter(
                    Q(username__icontains=search_query) | 
                    Q(email__icontains=search_query) |
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query)
                )
            
            context = {
                'users': users,
                'search_query': search_query,
                'user': request.user
            }
            
            return render(request, 'moderator/users_list.html', context)

class ModerUserAPIView(ModeratorRequiredMixin, View):
    """
    API для управления пользователями
    """
    @method_decorator(check_auth_tokens)
    def post(self, request, user_id):
        user_obj = get_object_or_404(User, id=user_id)
        data = json.loads(request.body.decode('utf-8'))
        action = data.get('action')
        
        if action == 'toggle_active':
            # Блокировка/разблокировка пользователя
            user_obj.is_active = not user_obj.is_active
            user_obj.save()
            
            logger.info(f"Модератор {request.user.username} изменил статус активности пользователя {user_obj.username} на {user_obj.is_active}")
            
            return JsonResponse({
                'status': 'success',
                'is_active': user_obj.is_active
            })
        
        elif action == 'update_profile':
            # Обновление данных пользователя
            first_name = data.get('first_name', user_obj.first_name)
            last_name = data.get('last_name', user_obj.last_name)
            email = data.get('email', user_obj.email)
            
            user_obj.first_name = first_name
            user_obj.last_name = last_name
            user_obj.email = email
            user_obj.save()
            
            logger.info(f"Модератор {request.user.username} обновил профиль пользователя {user_obj.username}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Профиль пользователя обновлен'
            })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Некорректное действие'
        }, status=400)

class ModerDeleteMessageAPIView(ModeratorRequiredMixin, View):
    """
    API для удаления сообщений модератором
    """
    @method_decorator(check_auth_tokens)
    def post(self, request, message_id):
        message = get_object_or_404(ChatMessage, id=message_id)
        
        # Сохраняем информацию о сообщении перед удалением
        room_name = message.room_name
        message_info = {
            'id': message.id,
            'user_id': message.user.id,
            'username': message.user.username,
            'message_text': message.message,
            'room_name': room_name
        }
        
        # Удаляем сообщение
        message.delete()
        
        logger.info(f"Модератор {request.user.username} удалил сообщение #{message_id} от пользователя {message_info['username']} в чате {room_name}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Сообщение удалено',
            'message_id': message_id,
            'room_name': room_name
        }) 