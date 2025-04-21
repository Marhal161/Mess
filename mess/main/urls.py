from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import RegisterView, LoginView, LogoutView, LoginTemplateView, RegisterTemplateView, InterestListView, HomeView, LikeUserView, ProfileTemplateView, ProfileView, ChangePasswordView
from .views.ChatView import ChatRoomView, ChatRoomListView
from .views.ChatApiView import ChatMessagesAPI
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/interests/', InterestListView.as_view(), name='interests_list'),
    path('api/like/<int:user_id>/', LikeUserView.as_view(), name='like_user'),
    path('auth/login/', LoginTemplateView.as_view(), name='login_page'),
    path('auth/register/', RegisterTemplateView.as_view(), name='register_page'),
    
    # Профиль пользователя
    path('profile/', ProfileTemplateView.as_view(), name='profile_page'),
    path('api/profile/', ProfileView.as_view(), name='profile_api'),
    path('api/profile/<int:user_id>/', ProfileView.as_view(), name='profile_user_api'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change_password_api'),
    path('api/profile/likes-count/', views.LikesCountView.as_view(), name='profile-likes-count'),
    
    # Обновление JWT токена
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Чат
    path('chat/', ChatRoomListView.as_view(), name='chat_rooms'),
    path('chat/<str:room_name>/', ChatRoomView.as_view(), name='chat_room'),
    
    # API чата
    path('api/chat/messages/<str:room_name>/', ChatMessagesAPI.as_view(), name='chat_messages_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)