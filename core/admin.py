from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Единственная запись: список не показываем, сразу открываем форму."""
    readonly_fields = ['icon_preview']
    fieldsets = (
        ('Название и иконка', {'fields': ('site_name', 'icon', 'icon_preview', 'fa_icon')}),
        ('Контакты для связи при ошибках сайта', {
            'fields': ('error_note', 'contact_phone', 'contact_email', 'contact_telegram',
                       'contact_address', 'working_hours'),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse('admin:core_sitesettings_change', args=[obj.pk]))

    def response_change(self, request, obj):
        self.message_user(request, 'Настройки сохранены — изменения уже видны на сайте.', messages.SUCCESS)
        return redirect(reverse('admin:core_sitesettings_change', args=[obj.pk]))

    @admin.display(description='Сейчас на сайте')
    def icon_preview(self, obj):
        if obj and obj.icon:
            return format_html('<img src="{}" alt="" style="width:56px;height:56px;border-radius:14px;object-fit:cover">', obj.icon.url)
        return format_html('<span class="site-fa-preview"><i class="fas {}"></i></span>', obj.fa_icon if obj else 'fa-bolt')
