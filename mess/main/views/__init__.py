"""
Этот файл делает директорию views Python-пакетом.
Здесь можно импортировать и предоставлять публичный API для views.
"""

from .LoginView import LoginView
from .LogoutView import LogoutView
from .AuthTemplateView import LoginTemplateView, RegisterTemplateView
from .RegisterView import RegisterView
from .ProfileView import ProfileTemplateView, ProfileView, ChangePasswordView
from .HomeView import HomeView
from .ChatView import ChatRoomListView, ChatRoomView
from .ChatApiView import ChatMessagesAPI, UnreadMessagesCountAPI, MarkMessagesAsReadAPI
from .LikeView import LikeUserView, CheckLikeView, LikesCountView
from .InterestView import InterestListView
from .AdminView import AdminPanelView, AdminUserEditView, AdminUserUpdateAPI, AdminUserToggleStatusAPI
from rest_framework_simplejwt.views import TokenRefreshView 