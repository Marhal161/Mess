from django.shortcuts import render
from django.views.generic import TemplateView

class LoginTemplateView(TemplateView):
    template_name = 'auth/login.html'

class RegisterTemplateView(TemplateView):
    template_name = 'auth/register.html'