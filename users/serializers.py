from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import CustomUser


def check_password_strength(password, user, field):
    """Те же правила, что и при сбросе пароля: валидаторы из AUTH_PASSWORD_VALIDATORS
    (минимум 8 символов, не из списка простых, не только цифры, не похож на email/логин)."""
    try:
        validate_password(password, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError({field: list(e.messages)})


class UserRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации"""
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'full_name', 'city', 'age', 'phone', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError('Пароли не совпадают')
        # временный объект пользователя — чтобы валидатор проверил похожесть на email/логин/ФИО
        candidate = CustomUser(
            email=data.get('email', ''), username=data.get('username', ''),
            full_name=data.get('full_name', ''),
        )
        check_password_strength(data['password'], candidate, 'password')
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для входа"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Неверный email или пароль')
        if not user.is_active:
            raise serializers.ValidationError('Аккаунт заблокирован')
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля"""

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'full_name', 'city', 'age', 'phone',
            'role', 'avatar', 'created_at', 'is_superuser', 'is_staff'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'created_at', 'is_superuser', 'is_staff'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор смены пароля"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError('Пароли не совпадают')
        check_password_strength(data['new_password'], self.context['request'].user, 'new_password')
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Неверный старый пароль')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

