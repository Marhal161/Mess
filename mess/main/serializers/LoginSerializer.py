from rest_framework import serializers
from django.contrib.auth import authenticate

class LogSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        password = data['password']

        username = email.split('@')[0]  # Берем часть до "@"

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError('Неверный email или пароль')

        data['user'] = user
        return data