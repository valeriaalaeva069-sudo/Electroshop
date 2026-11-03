from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings


def site_payload(site, request=None):
    icon = site.icon.url if site.icon else None
    if icon and request is not None:
        icon = request.build_absolute_uri(icon)
    return {
        'site_name': site.site_name,
        'icon': icon,
        'fa_icon': site.fa_icon,
        'error_note': site.error_note,
        'contacts': {
            'phone': site.contact_phone,
            'email': site.contact_email,
            'telegram': site.contact_telegram,
            'address': site.contact_address,
            'working_hours': site.working_hours,
        },
    }


class SiteSettingsView(APIView):
    """Название, иконка и контакты сайта (публично, только чтение; менять — в админке)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(site_payload(SiteSettings.load(), request))
