"""
Этот файл делает директорию views Python-пакетом.
Здесь можно импортировать и предоставлять публичный API для views.
"""

from .RegisterView import RegisterView
from .LoginView import LoginView
from .LogoutView import LogoutView
from .AuthTemplateView import LoginTemplateView, RegisterTemplateView
from .InterestView import InterestListView
from .HomeView import HomeView
from .LikeView import LikeUserView, LikesCountView
from .ProfileView import ProfileTemplateView, ProfileView, ChangePasswordView 