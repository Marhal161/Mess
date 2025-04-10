from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11, validators=[MaxValueValidator(11)])
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    interests = models.ManyToManyField('Interest', related_name='users', blank=True)
    roles = models.ManyToManyField('Role', related_name='users', blank=True)

class Role(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name 