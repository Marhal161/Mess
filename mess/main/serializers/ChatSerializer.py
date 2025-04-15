from rest_framework import serializers
from main.models import ChatRoom, Message, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp', 'is_read']

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'participants', 'created_at', 'last_message']
        read_only_fields = ['id', 'created_at']
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None