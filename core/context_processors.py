from .models import SiteSettings
from .views import site_payload


def site_settings(request):
    """Делает настройки сайта доступными во всех шаблонах: {{ site }} и site_contact (для JavaScript)."""
    try:
        site = SiteSettings.load()
    except Exception:  # например, таблица ещё не создана (до migrate)
        site = SiteSettings(pk=1)
    return {'site': site, 'site_contact': site_payload(site)}
