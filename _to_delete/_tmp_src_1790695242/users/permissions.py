from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Разрешение только для администраторов (role='admin' или is_superuser)"""

    def has_permission(self, request, view):
        return (
                request.user.is_authenticated and
                (request.user.is_superuser or request.user.role == 'admin')
        )