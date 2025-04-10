from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views.RegisterView import RegisterView
from .views.LoginView import LoginView
from .views.LogoutView import LogoutView
from .views.AuthTemplateView import LoginTemplateView, RegisterTemplateView
from .views.InterestView import InterestListView
from .views.HomeView import HomeView
from .views.LikeView import LikeUserView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/interests/', InterestListView.as_view(), name='interests_list'),
    path('api/like/<int:user_id>/', LikeUserView.as_view(), name='like_user'),
    path('auth/login/', LoginTemplateView.as_view(), name='login_page'),
    path('auth/register/', RegisterTemplateView.as_view(), name='register_page'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)