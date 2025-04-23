from django.views.generic import TemplateView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.urls import reverse
from main.models import User, Interest, Role
from main.decorators import check_auth_tokens
from django.db import transaction
from django.utils.decorators import method_decorator
import logging
import json

logger = logging.getLogger(__name__)

class AdminRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки, что пользователь является администратором"""
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        
        # Проверяем наличие роли "Admin" у пользователя
        admin_role = Role.objects.filter(name="Admin").first()
        if not admin_role:
            logger.warning("Роль Admin не найдена в базе данных")
            return False
            
        return self.request.user.role.filter(id=admin_role.id).exists()
    
    def handle_no_permission(self):
        return redirect('home')

@method_decorator(check_auth_tokens, name='dispatch')
class AdminPanelView(AdminRequiredMixin, TemplateView):
    """Представление для главной страницы админ-панели"""
    template_name = 'admin/admin_panel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем всех пользователей, кроме суперпользователя и текущего пользователя
        users = User.objects.exclude(is_superuser=True).exclude(id=self.request.user.id).order_by('username')
        
        # Получаем роли Admin и Moder
        admin_role = Role.objects.filter(name="Admin").first()
        moder_role = Role.objects.filter(name="Moder").first()
        
        # Счетчики для статистики
        active_users_count = 0
        inactive_users_count = 0
        admin_users_count = 0
        
        # Обогащаем данные пользователей информацией о ролях
        for user in users:
            # Получаем имена ролей для отображения
            role_names = [role.name for role in user.role.all()]
            user.roles = role_names
            
            # Флаги для проверки наличия конкретных ролей
            user.is_admin = admin_role and user.role.filter(id=admin_role.id).exists()
            user.is_moder = moder_role and user.role.filter(id=moder_role.id).exists()
            
            # Увеличиваем счетчики
            if user.is_active:
                active_users_count += 1
            else:
                inactive_users_count += 1
                
            if user.is_admin:
                admin_users_count += 1
        
        context['users'] = users
        context['active_users_count'] = active_users_count
        context['inactive_users_count'] = inactive_users_count
        context['admin_users_count'] = admin_users_count
        
        return context

@method_decorator(check_auth_tokens, name='dispatch')
class AdminUserEditView(AdminRequiredMixin, TemplateView):
    """Представление для редактирования пользователя администратором"""
    template_name = 'admin/admin_user_edit.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем пользователя по ID
        user_id = kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        # Получаем все доступные интересы
        interests = Interest.objects.all().order_by('name')
        
        # Получаем все доступные роли
        roles = Role.objects.all()
        
        context['edit_user'] = user
        context['interests'] = interests
        context['roles'] = roles
        context['selected_interests'] = [interest.id for interest in user.interests.all()]
        context['selected_roles'] = [role.id for role in user.role.all()]
        context['admin_role'] = Role.objects.filter(name="Admin").first()
        return context

@method_decorator(check_auth_tokens, name='dispatch')
class AdminUserUpdateAPI(AdminRequiredMixin, View):
    """API для обновления данных пользователя администратором"""
    
    def post(self, request, user_id):
        try:
            with transaction.atomic():
                user = get_object_or_404(User, id=user_id)
                
                # Получаем данные из POST запроса
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                phone = request.POST.get('phone')
                bio = request.POST.get('bio')
                gender = request.POST.get('gender')
                kurs = request.POST.get('kurs')
                
                # Проверка уникальности email
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Email уже используется другим пользователем'
                    }, status=400)
                
                # Обновляем основные поля
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.phone = phone
                user.bio = bio
                user.gender = gender
                user.kurs = kurs
                
                # Обрабатываем роли
                if 'roles' in request.POST:
                    roles_ids = request.POST.getlist('roles')
                    # Очищаем текущие роли и добавляем новые
                    user.role.clear()
                    roles = Role.objects.filter(id__in=roles_ids)
                    user.role.add(*roles)
                    
                    # Проверяем, есть ли роль Admin, и устанавливаем is_staff соответственно
                    admin_role = Role.objects.filter(name="Admin").first()
                    if admin_role and admin_role.id in [int(role_id) for role_id in roles_ids]:
                        user.is_staff = True
                    else:
                        user.is_staff = False
                
                # Обрабатываем статус активности
                is_active = request.POST.get('is_active') == 'on'
                user.is_active = is_active
                
                # Обрабатываем интересы
                if 'interests' in request.POST:
                    interests_ids = request.POST.getlist('interests')
                    # Очищаем текущие интересы и добавляем новые
                    user.interests.clear()
                    interests = Interest.objects.filter(id__in=interests_ids)
                    user.interests.add(*interests)
                
                # Сбрасываем пароль, если нужно
                if 'reset_password' in request.POST and request.POST.get('reset_password') == 'on':
                    new_password = request.POST.get('new_password')
                    if new_password:
                        user.set_password(new_password)
                
                user.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Данные пользователя успешно обновлены',
                    'redirect': reverse('admin_panel')
                })
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)
            
@method_decorator(check_auth_tokens, name='dispatch')
class AdminUserToggleStatusAPI(AdminRequiredMixin, View):
    """API для быстрого переключения статуса пользователя"""
    
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Получаем данные из JSON
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'toggle_admin':
                # Переключаем статус администратора
                admin_role = Role.objects.filter(name="Admin").first()
                if not admin_role:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Роль администратора не найдена'
                    }, status=400)
                
                if user.role.filter(id=admin_role.id).exists():
                    # Удаляем роль Admin
                    user.role.remove(admin_role)
                    user.is_staff = False
                    message = "Пользователь больше не администратор"
                    is_admin = False
                else:
                    # Добавляем роль Admin
                    user.role.add(admin_role)
                    user.is_staff = True
                    message = "Пользователь теперь администратор"
                    is_admin = True
                
                user.save()
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'is_admin': is_admin
                })
                    
            elif action == 'toggle_moder':
                # Переключаем статус модератора
                moder_role = Role.objects.filter(name="Moder").first()
                if not moder_role:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Роль модератора не найдена'
                    }, status=400)
                
                if user.role.filter(id=moder_role.id).exists():
                    # Удаляем роль Moder
                    user.role.remove(moder_role)
                    message = "Пользователь больше не модератор"
                    is_moder = False
                else:
                    # Добавляем роль Moder
                    user.role.add(moder_role)
                    message = "Пользователь теперь модератор"
                    is_moder = True
                
                user.save()
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'is_moder': is_moder
                })
                
            elif action == 'toggle_active':
                # Переключаем активность аккаунта
                user.is_active = not user.is_active
                message = f"Аккаунт пользователя {'активирован' if user.is_active else 'деактивирован'}"
                
                user.save()
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'is_active': user.is_active
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неизвестное действие'
                }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"Ошибка при переключении статуса пользователя: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)

@method_decorator(check_auth_tokens, name='dispatch')
class AdminInterestAPI(AdminRequiredMixin, View):
    """API для управления интересами"""
    
    def get(self, request):
        """Получение списка всех интересов"""
        try:
            interests = Interest.objects.all().order_by('name')
            interests_data = []
            
            for interest in interests:
                interest_data = {
                    'id': interest.id,
                    'name': interest.name,
                    'description': interest.description,
                    'icon': interest.icon.url if interest.icon else None
                }
                interests_data.append(interest_data)
            
            return JsonResponse(interests_data, safe=False)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка интересов: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """Создание нового интереса"""
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            icon = request.FILES.get('icon')
            
            # Проверка наличия обязательных полей
            if not name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Название интереса обязательно'
                }, status=400)
            
            # Проверка уникальности имени
            if Interest.objects.filter(name=name).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Интерес с таким названием уже существует'
                }, status=400)
            
            # Создание нового интереса
            interest = Interest(
                name=name,
                description=description
            )
            
            if icon:
                interest.icon = icon
                
            interest.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Интерес успешно создан',
                'interest': {
                    'id': interest.id,
                    'name': interest.name,
                    'description': interest.description,
                    'icon': interest.icon.url if interest.icon else None
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка при создании интереса: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)

@method_decorator(check_auth_tokens, name='dispatch')
class AdminInterestDetailAPI(AdminRequiredMixin, View):
    """API для управления отдельным интересом"""
    
    def get(self, request, interest_id):
        """Получение данных интереса по ID"""
        try:
            interest = get_object_or_404(Interest, id=interest_id)
            
            interest_data = {
                'id': interest.id,
                'name': interest.name,
                'description': interest.description,
                'icon': interest.icon.url if interest.icon else None
            }
            
            return JsonResponse(interest_data)
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных интереса: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)
    
    def put(self, request, interest_id):
        """Обновление интереса"""
        try:
            interest = get_object_or_404(Interest, id=interest_id)
            
            # Улучшенное извлечение данных из запроса
            try:
                # Пытаемся извлечь данные как JSON
                if request.content_type and 'application/json' in request.content_type:
                    data = json.loads(request.body)
                    name = data.get('name')
                    description = data.get('description', '')
                else:
                    # Форма данных или другой тип
                    name = request.POST.get('name')
                    description = request.POST.get('description', '')
                    
                # Дополнительная проверка и логирование
                logger.debug(f"Полученные данные для интереса: name='{name}', description='{description}', content_type={request.content_type}")
            except Exception as e:
                logger.error(f"Ошибка при извлечении данных запроса: {e}")
                name = None
                description = ''
            
            # Проверка наличия обязательных полей
            if not name or name.strip() == '':
                logger.warning(f"Попытка обновления интереса без имени: {interest_id}, request_data={request.POST}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Название интереса обязательно'
                }, status=400)
            
            # Очистка имени от лишних пробелов
            name = name.strip()
            
            # Проверка уникальности имени
            if Interest.objects.filter(name=name).exclude(id=interest_id).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Интерес с таким названием уже существует'
                }, status=400)
            
            # Обновление данных
            interest.name = name
            interest.description = description
            
            if 'icon' in request.FILES:
                interest.icon = request.FILES['icon']
                
            interest.save()
            
            logger.info(f"Интерес успешно обновлен: id={interest_id}, name='{name}'")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Интерес успешно обновлен',
                'interest': {
                    'id': interest.id,
                    'name': interest.name,
                    'description': interest.description,
                    'icon': interest.icon.url if interest.icon else None
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении интереса: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)
    
    def delete(self, request, interest_id):
        """Удаление интереса"""
        try:
            interest = get_object_or_404(Interest, id=interest_id)
            
            # Проверка, связан ли интерес с пользователями
            users_count = interest.users.count()
            if users_count > 0:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Невозможно удалить интерес, он используется {users_count} пользователями'
                }, status=400)
            
            # Удаление интереса
            interest_name = interest.name
            interest.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Интерес "{interest_name}" успешно удален'
            })
            
        except Exception as e:
            logger.error(f"Ошибка при удалении интереса: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500)

@method_decorator(check_auth_tokens, name='dispatch')
class AdminRolesAPI(AdminRequiredMixin, View):
    """API для получения списка ролей"""
    
    def get(self, request):
        """Получение списка всех ролей"""
        try:
            roles = Role.objects.all().order_by('name')
            roles_data = []
            
            for role in roles:
                role_data = {
                    'id': role.id,
                    'name': role.name,
                    'description': role.description
                }
                roles_data.append(role_data)
            
            return JsonResponse(roles_data, safe=False)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка ролей: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Произошла ошибка: {str(e)}'
            }, status=500) 