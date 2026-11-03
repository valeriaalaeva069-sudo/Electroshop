from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="API Интернет-магазина электроники",
        default_version='v1',
        description="""
        REST API для интернет-магазина электроники.

        **Возможности:**
        * 🛍️ Каталог товаров с фильтрацией
        * 🛒 Корзина покупателя
        * 📦 Оформление и отслеживание заказов
        * 👤 Регистрация и аутентификация (JWT)
        * 📊 Аналитика и отчёты (Excel/PDF)
        * 🔔 Уведомления в реальном времени (WebSockets)

        **Авторизация:**
        1. Зарегистрируйтесь через `/api/auth/register/`
        2. Войдите через `/api/auth/login/` — получите токен
        3. Нажмите кнопку "Authorize" вверху и введите: `Bearer <ваш_токен>`
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="admin@shop.ru"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)