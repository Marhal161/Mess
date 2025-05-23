from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MaxValueValidator
import os
from django.utils import timezone
import random
import string

def get_avatar_path(instance, filename):
    """
    Функция определяет путь для сохранения аватара пользователя.
    Создает структуру: media/profiles/username/filename
    """
    # Очистка имени пользователя от спецсимволов и приведение к нижнему регистру
    username = ''.join(c for c in instance.username if c.isalnum() or c == '_').lower()
    # Возвращаем путь относительно MEDIA_ROOT
    return os.path.join('profiles', username, filename)

class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='icons/', null=True, blank=True)

    def __str__(self):
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11)
    avatar = models.ImageField(upload_to=get_avatar_path, null=True, blank=True)
    bio = models.TextField(blank=True)
    interests = models.ManyToManyField(Interest, related_name='users', blank=True)
    role = models.ManyToManyField(Role, related_name='users_with_role', blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Мужчина'), ('female', 'Женщина')], null=True, blank=True)
    kurs = models.CharField(max_length=10, choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], null=True, blank=True)
    has_warnings = models.BooleanField(default=False, verbose_name="Имеет предупреждения")

    def __str__(self):
        return self.username

class Like(models.Model):
    from_user = models.ForeignKey(User, related_name='likes_given', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='likes_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Уникальное ограничение чтобы пользователь не мог лайкнуть одного человека дважды
        unique_together = ('from_user', 'to_user')
        
    def __str__(self):
        return f"{self.from_user.username} лайкнул {self.to_user.username}"

class GroupChat(models.Model):
    """
    Модель группового чата
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_group_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name='group_chats')
    is_private = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='group_chats/avatars/', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Group Chat: {self.name}"
    
    def get_room_name(self):
        return f"group_{self.id}"
        
    def get_display_name(self):
        return self.name

class ChatMessage(models.Model):
    """
    Модель сообщения чата
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    room_name = models.CharField(max_length=100)  # Может быть direct_X_Y или group_X
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    edited = models.BooleanField(default=False)
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"
    
    def is_group_message(self):
        return self.room_name.startswith('group_')

class ChatReport(models.Model):
    """
    Модель для хранения жалоб на чат
    """
    REPORT_STATUS = [
        ('pending', 'На рассмотрении'),
        ('processed', 'Обработано'),
        ('rejected', 'Отклонено'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    room_name = models.CharField(max_length=100)
    description = models.TextField(verbose_name="Описание проблемы")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    moderator_notes = models.TextField(blank=True, verbose_name="Заметки модератора")
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_reports')
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Жалоба от {self.reporter.username} на чат {self.room_name}"

class UserWarning(models.Model):
    """
    Модель для хранения предупреждений пользователей
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    report = models.ForeignKey(ChatReport, on_delete=models.CASCADE, related_name='warnings')
    created_at = models.DateTimeField(auto_now_add=True)
    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='given_warnings')
    reason = models.TextField(verbose_name="Причина предупреждения")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Предупреждение для {self.user.username} от {self.moderator.username if self.moderator else 'неизвестно'}"
