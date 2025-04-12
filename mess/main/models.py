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
