from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.db.models import Q, Exists, OuterRef, BooleanField, Case, When, Count
from main.models import User, Like, Interest
from main.decorators import check_auth_tokens
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger(__name__)

@method_decorator(check_auth_tokens, name='dispatch')
class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get(self, request, *args, **kwargs):
        # Проверяем, аутентифицирован ли пользователь
        if not request.user.is_authenticated:
            return redirect('login_page')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Подзапрос для определения, лайкнул ли текущий пользователь профиль
        liked_subquery = Like.objects.filter(
            from_user=user,
            to_user=OuterRef('pk')
        )
        
        # Начинаем с общего запроса, исключающего текущего пользователя, админов и персонал
        base_query = User.objects.exclude(
            Q(pk=user.pk) |  # Исключаем текущего пользователя
            Q(is_superuser=True) |  # Исключаем администраторов
            Q(is_staff=True)  # Исключаем персонал
        )
        
        # Получаем список ID интересов для фильтрации (если есть)
        interest_ids = self.request.GET.getlist('interests')
        
        # Если указаны интересы для фильтрации
        if interest_ids:
            try:
                # Преобразуем строковые ID в целые числа
                interest_ids = [int(id) for id in interest_ids if id.isdigit()]
                
                if interest_ids:
                    # Фильтруем пользователей по интересам
                    # Используем distinct() чтобы избежать дублирования пользователей при совпадении нескольких интересов
                    base_query = base_query.filter(
                        interests__id__in=interest_ids
                    ).distinct()
                    
                    # Логируем для отладки
                    logger.debug(f"Фильтрация пользователей по интересам: {interest_ids}")
                
            except Exception as e:
                logger.error(f"Ошибка при фильтрации по интересам: {e}")
        
        # Добавляем is_liked и применяем случайную сортировку
        users = base_query.annotate(
            is_liked=Exists(liked_subquery)
        ).order_by('?')
        
        logger.debug(f"Найдено {users.count()} пользователей после фильтрации")
        
        context['users'] = users
        return context 