from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.db.models import Q, Exists, OuterRef, BooleanField, Case, When
from main.models import User, Like
from main.decorators import check_auth_tokens
from django.utils.decorators import method_decorator

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
        
        # Получаем всех пользователей кроме текущего, администраторов и персонала
        users = User.objects.exclude(
            Q(pk=user.pk) |  # Исключаем текущего пользователя
            Q(is_superuser=True) |  # Исключаем администраторов
            Q(is_staff=True)  # Исключаем персонал
        ).annotate(
            # Добавляем поле is_liked, которое показывает, лайкнул ли текущий пользователь этот профиль
            is_liked=Exists(liked_subquery)
        ).order_by('?')  # Случайный порядок
        
        context['users'] = users
        return context 