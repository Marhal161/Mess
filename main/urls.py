from django.urls import path
from main.views.ChatView import ChatRoomListView, ChatRoomView, GroupChatListView
from main.views.GroupChatAPI import GroupChatAPI

urlpatterns = [
    # Чат
    path('chat/', ChatRoomListView.as_view(), name='chat_rooms'),
    path('chat/<str:room_name>/', ChatRoomView.as_view(), name='chat_room'),
    path('group-chats/', GroupChatListView.as_view(), name='group_chats'),
    
    # API чата
    path('api/group-chats/', GroupChatAPI.as_view(), name='group_chats_api'),
] 