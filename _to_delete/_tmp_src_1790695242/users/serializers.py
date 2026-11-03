from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db import models
from .models import CustomUser


class UserRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации"""
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'full_name', 'city', 'age', 'phone', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError('Пароли не совпадают')
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
    new_password = serializers.CharField(write_only=True, min_length=6)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError('Пароли не совпадают')
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


class AdminUserListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка пользователей (админ)"""
    orders_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'full_name', 'city', 'age', 'phone',
            'role', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login', 'orders_count', 'total_spent'
        ]

    def get_orders_count(self, obj):
        return obj.orders.count()

    def get_total_spent(self, obj):
        total = obj.orders.aggregate(total=models.Sum('total_amount'))['total']
        return float(total) if total else 0


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для редактирования пользователя (админ)"""

    class Meta:
        model = CustomUser
        fields = ['full_name', 'city', 'age', 'phone', 'role', 'is_active']

    def validate_role(self, value):
        if value not in ['guest', 'customer', 'admin']:
            raise serializers.ValidationError('Недопустимая роль')
        return value