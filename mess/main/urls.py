from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views.LoginView import LoginView
from .views.LogoutView import LogoutView
from .views.AuthTemplateView import LoginTemplateView, RegisterTemplateView
from .views.RegisterView import RegisterView
from .views.InterestView import InterestListView
from .views.HomeView import HomeView
from .views.ProfileView import ProfileTemplateView, ProfileView, ChangePasswordView
from .views.ChatView import ChatRoomView, ChatRoomListView
from .views.ChatApiView import ChatMessagesAPI, UnreadMessagesCountAPI, MarkMessagesAsReadAPI, ChatListAPI, EditMessageAPI, DeleteMessageAPI, ReportChatAPI
from .views.LikeView import LikeUserView, CheckLikeView, LikesCountView
from .views.AdminView import (
    AdminPanelView, AdminUserEditView, AdminUserUpdateAPI, AdminUserToggleStatusAPI,
    AdminInterestAPI, AdminInterestDetailAPI, AdminRolesAPI
)
from .views.ModerView import (
    ModeratorPanelView, ReportListView, ReportDetailView, 
    ModerUserManagementView, ModerUserAPIView, ModerDeleteMessageAPIView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/interests/', InterestListView.as_view(), name='interests_list'),
    path('api/like/<int:user_id>/', LikeUserView.as_view(), name='like_user'),
    path('api/like/check/<int:user_id>/', CheckLikeView.as_view(), name='check_like'),
    path('auth/login/', LoginTemplateView.as_view(), name='login_page'),
    path('auth/register/', RegisterTemplateView.as_view(), name='register_page'),
    
    # Профиль пользователя
    path('profile/', ProfileTemplateView.as_view(), name='profile_page'),
    path('profile/<int:user_id>/', ProfileTemplateView.as_view(), name='profile_user_page'),
    path('api/profile/', ProfileView.as_view(), name='profile_api'),
    path('api/profile/<int:user_id>/', ProfileView.as_view(), name='profile_user_api'),
    path('api/change-password/', ChangePasswordView.as_view(), name='change_password_api'),
    path('api/profile/likes-count/', LikesCountView.as_view(), name='profile-likes-count'),
    
    # Обновление JWT токена
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Чат
    path('chat/', ChatRoomListView.as_view(), name='chat_rooms'),
    path('chat/<str:room_name>/', ChatRoomView.as_view(), name='chat_room'),
    
    # API чата
    path('api/chat/messages/<str:room_name>/', ChatMessagesAPI.as_view(), name='chat_messages_api'),
    path('api/chat/unread-count/', UnreadMessagesCountAPI.as_view(), name='unread_messages_count'),
    path('api/chat/mark-read/<str:room_name>/', MarkMessagesAsReadAPI.as_view(), name='mark_messages_read'),
    path('api/chat/list/', ChatListAPI.as_view(), name='chat_list_api'),
    path('api/chat/edit-message/<int:message_id>/', EditMessageAPI.as_view(), name='edit_message_api'),
    path('api/chat/delete-message/<int:message_id>/', DeleteMessageAPI.as_view(), name='delete_message_api'),
    path('api/chat/report/<str:room_name>/', ReportChatAPI.as_view(), name='report_chat_api'),
    
    # Админ-панель
    path('admin-panel/', AdminPanelView.as_view(), name='admin_panel'),
    path('admin-panel/user/<str:user_id>/', AdminUserEditView.as_view(), name='admin_user_edit'),
    path('admin-panel/user/<str:user_id>/update/', AdminUserUpdateAPI.as_view(), name='admin_user_update'),
    path('admin-panel/user/<str:user_id>/toggle-status/', AdminUserToggleStatusAPI.as_view(), name='admin_user_toggle_status'),
    
    # Admin API для интересов
    path('api/admin/interests/', AdminInterestAPI.as_view(), name='admin_interests_api'),
    path('api/admin/interests/<int:interest_id>/', AdminInterestDetailAPI.as_view(), name='admin_interest_detail_api'),
    path('api/admin/roles/', AdminRolesAPI.as_view(), name='admin_roles_api'),
    
    # Панель модератора
    path('moderator/', ModeratorPanelView.as_view(), name='moder_panel'),
    path('moderator/reports/', ReportListView.as_view(), name='moder_reports_list'),
    path('moderator/reports/<int:report_id>/', ReportDetailView.as_view(), name='moder_report_detail'),
    path('moderator/users/', ModerUserManagementView.as_view(), name='moder_users_list'),
    path('moderator/users/<int:user_id>/', ModerUserManagementView.as_view(), name='moder_user_detail'),
    
    # API для модераторов
    path('api/moderator/user/<int:user_id>/', ModerUserAPIView.as_view(), name='moder_user_api'),
    path('api/moderator/message/delete/<int:message_id>/', ModerDeleteMessageAPIView.as_view(), name='moder_delete_message_api'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)