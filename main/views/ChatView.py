from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from main.decorators import check_auth_tokens
from ..models import GroupChat
import logging

logger = logging.getLogger(__name__)

@method_decorator(check_auth_tokens, name='dispatch')
class ChatRoomListView(LoginRequiredMixin, TemplateView):
    template_name = 'chat_rooms.html'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_page')
        return super().get(request, *args, **kwargs)

@method_decorator(check_auth_tokens, name='dispatch')
class GroupChatListView(LoginRequiredMixin, TemplateView):
    template_name = 'group_chats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group_chats'] = GroupChat.objects.filter(members=self.request.user)
        return context
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_page')
        return super().get(request, *args, **kwargs)

@method_decorator(check_auth_tokens, name='dispatch')
class ChatRoomView(LoginRequiredMixin, TemplateView):
    template_name = 'chat_room.html'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_page')
        return super().get(request, *args, **kwargs) 