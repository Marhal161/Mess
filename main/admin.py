from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Interest, Role

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('phone', 'avatar', 'bio', 'interests', 'role', 'gender', 'kurs')}),
    )
    filter_horizontal = ('interests', 'role', 'groups', 'user_permissions')
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('email', 'phone', 'avatar', 'bio', 'interests', 'role', 'gender', 'kurs')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone') 