from rest_framework.permissions import BasePermission


def is_shop_admin(user):
    """Единое правило «кто админ магазина»: role='admin' или суперпользователь.
    Используется везде — в API, WebSocket и шаблонах, чтобы проверки не расходились."""
    return bool(
        user and user.is_authenticated and
        (user.is_superuser or getattr(user, 'role', None) == 'admin')
    )


class IsAdminRole(BasePermission):
    """Разрешение только для администраторов (role='admin' или is_superuser)"""

    def has_permission(self, request, view):
        return is_shop_admin(request.user)
