from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),
    path('auth/password/change/', views.PasswordChangeView.as_view(), name='password-change'),
    path('auth/password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]