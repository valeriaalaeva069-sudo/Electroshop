import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from users.models import CustomUser
from .models import SiteSettings


def make_png(name='icon.png'):
    buf = BytesIO()
    Image.new('RGB', (64, 64), '#5B3DF5').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class SiteSettingsModelTests(TestCase):
    def test_singleton(self):
        a = SiteSettings.load()
        b = SiteSettings(site_name='Другое')
        b.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().site_name, 'Другое')
        SiteSettings.load().delete()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(a.pk, 1)

    def test_hrefs(self):
        s = SiteSettings.load()
        s.contact_phone = '+7 (900) 111-22-33'
        s.contact_telegram = '@shop_help'
        self.assertEqual(s.phone_href, '+79001112233')
        self.assertEqual(s.telegram_href, 'https://t.me/shop_help')


class SitePagesTests(TestCase):
    def setUp(self):
        s = SiteSettings.load()
        s.site_name = 'МегаТех'
        s.contact_phone = '+7 (900) 111-22-33'
        s.contact_email = 'help@megatech.ru'
        s.save()

    def test_name_and_contacts_on_pages(self):
        for url in ('/', '/contacts/'):
            html = self.client.get(url).content.decode()
            self.assertIn('МегаТех', html)
            self.assertIn('help@megatech.ru', html)
            self.assertIn('+7 (900) 111-22-33', html)

    def test_api(self):
        data = self.client.get('/api/site-settings/').json()
        self.assertEqual(data['site_name'], 'МегаТех')
        self.assertEqual(data['contacts']['email'], 'help@megatech.ru')

    def test_404_page_has_contacts(self):
        resp = self.client.get('/no-such-page/')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('help@megatech.ru', resp.content.decode())


class SiteSettingsAdminTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        self.admin = CustomUser.objects.create_superuser(
            username='root', email='root@x.ru', password='pass12345', full_name='Root')
        self.client.force_login(self.admin)
        SiteSettings.load()

    def test_non_staff_has_no_access(self):
        self.client.logout()
        user = CustomUser.objects.create_user(
            username='u', email='u@x.ru', password='pass12345', full_name='U')
        self.client.force_login(user)
        resp = self.client.get('/admin/core/sitesettings/1/change/')
        self.assertEqual(resp.status_code, 302)

    def test_changelist_redirects_to_form(self):
        resp = self.client.get('/admin/core/sitesettings/')
        self.assertEqual(resp.status_code, 302)

    def test_rename_and_icon_upload(self):
        with override_settings(MEDIA_ROOT=self.media):
            resp = self.client.post('/admin/core/sitesettings/1/change/', {
                'site_name': 'Новый магазин',
                'fa_icon': 'fa-bolt',
                'contact_phone': '+7 (999) 000-11-22',
                'contact_email': 'new@shop.ru',
                'contact_telegram': '',
                'contact_address': '',
                'working_hours': '',
                'error_note': 'Пишите нам',
                'icon': make_png(),
            })
            self.assertEqual(resp.status_code, 302)
            s = SiteSettings.load()
            self.assertEqual(s.site_name, 'Новый магазин')
            self.assertTrue(s.icon)
            html = self.client.get('/').content.decode()
            self.assertIn('Новый магазин', html)
            self.assertIn(s.icon.url, html)
            admin_html = self.client.get('/admin/').content.decode()
            self.assertIn('Новый магазин', admin_html)

    def test_admin_pages_open(self):
        for url in ('/admin/', '/admin/products/product/add/',
                    '/admin/products/category/add/', '/admin/core/sitesettings/1/change/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)
