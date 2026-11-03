import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
)


def get_tokens_for_user(user):
    """Генерация JWT-токенов"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = get_tokens_for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """Вход в систему"""
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        tokens = get_tokens_for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': tokens
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и редактирование профиля"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """Смена пароля"""
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Пароль успешно изменён'})


logger = logging.getLogger(__name__)


class PasswordResetRequestView(generics.GenericAPIView):
    """Запрос ссылки для сброса пароля. Всегда отвечает одинаково,
    чтобы нельзя было выяснить, зарегистрирован ли email."""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        if not email:
            return Response({'error': 'Укажите email'}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = request.build_absolute_uri(f'/password-reset/confirm/?uid={uid}&token={token}')
            try:
                if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                    send_mail(
                        'Сброс пароля — ElectroShop',
                        f'Чтобы задать новый пароль, перейдите по ссылке:\n{link}\n\n'
                        'Если это были не вы, просто проигнорируйте письмо.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                    )
                elif settings.DEBUG:
                    # SMTP не настроен — в разработке печатаем ссылку в консоль сервера
                    logger.warning('Ссылка для сброса пароля (DEBUG): %s', link)
                else:
                    logger.error('SMTP не настроен — письмо для сброса пароля не отправлено')
            except Exception:
                logger.exception('Не удалось отправить письмо для сброса пароля')

        return Response({'message': 'Если такой email зарегистрирован, мы отправили на него ссылку'})


class PasswordResetConfirmView(generics.GenericAPIView):
    """Установка нового пароля по ссылке из письма"""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        password = request.data.get('new_password', '')

        try:
            user = CustomUser.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, token):
            return Response({'error': 'Ссылка недействительна или устарела'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password, user)
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        return Response({'message': 'Пароль изменён. Теперь можно войти'})
