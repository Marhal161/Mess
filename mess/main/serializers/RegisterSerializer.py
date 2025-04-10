from rest_framework import serializers
from ..models import User, Interest
from django.core.validators import RegexValidator


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex='^[0-9]{11}$',
                message='Номер телефона должен содержать 11 цифр'
            )
        ]
    )
    avatar = serializers.ImageField(write_only=True, required=False)
    bio = serializers.CharField(write_only=True, required=False)
    gender = serializers.ChoiceField(choices=[('male', 'Мужчина'), ('female', 'Женщина')], required=False)
    kurs = serializers.ChoiceField(choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], required=False)
    interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Interest.objects.all(),
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password', 'phone', 'avatar', 'bio', 'gender', 'kurs', 'interests')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'validators': []}  # Отключаем стандартные валидаторы email
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def create(self, validated_data):
        # Извлекаем email и генерируем username
        email = validated_data['email']
        username = email.split('@')[0]  # Берем часть до "@"

        # Проверяем, занят ли username
        if User.objects.filter(username=username).exists():
            # Если username занят, генерируем уникальный, добавляя номер
            i = 1
            while True:
                new_username = f"{username}_{i}"
                if not User.objects.filter(username=new_username).exists():
                    username = new_username
                    break
                i += 1

        # Извлекаем interests
        interests = validated_data.pop('interests', [])
        
        password = validated_data.pop('password')
        user = User.objects.create_user(username=username, **validated_data, password=password)
        
        # Устанавливаем interests
        user.interests.set(interests)
        user.save()
        
        return user