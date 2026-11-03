from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

User = get_user_model()


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email='u@test.ru', username='u', full_name='U', password='OldPass12345!')

    def test_request_is_same_for_known_and_unknown_email(self):
        a = self.client.post('/api/auth/password/reset/', {'email': 'u@test.ru'}, format='json')
        b = self.client.post('/api/auth/password/reset/', {'email': 'nobody@test.ru'}, format='json')
        self.assertEqual(a.status_code, 200)
        self.assertEqual(a.data, b.data)

    def test_confirm_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        r = self.client.post('/api/auth/password/reset/confirm/',
                             {'uid': uid, 'token': token, 'new_password': 'BrandNew98765!'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew98765!'))

    def test_bad_token_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        r = self.client.post('/api/auth/password/reset/confirm/',
                             {'uid': uid, 'token': 'bad', 'new_password': 'BrandNew98765!'}, format='json')
        self.assertEqual(r.status_code, 400)


class PasswordRulesTests(APITestCase):
    def register(self, password):
        return self.client.post('/api/auth/register/', {
            'email': 'new@test.ru', 'username': 'newbie', 'full_name': 'New User',
            'password': password, 'password2': password}, format='json')

    def test_weak_password_rejected_on_register(self):
        for weak in ['12345678', 'qwerty', 'abc12']:
            r = self.register(weak)
            self.assertEqual(r.status_code, 400, weak)
            self.assertIn('password', r.data)

    def test_strong_password_accepted_on_register(self):
        self.assertEqual(self.register('Sunny-Kettle-42').status_code, 201)

    def test_weak_password_rejected_on_change(self):
        user = User.objects.create_user(
            email='u@test.ru', username='u', full_name='U', password='OldPass12345!')
        self.client.force_authenticate(user)
        r = self.client.post('/api/auth/password/change/', {
            'old_password': 'OldPass12345!', 'new_password': '1234567', 'new_password2': '1234567'},
            format='json')
        self.assertEqual(r.status_code, 400)


class AdminRoleSyncTests(APITestCase):
    def test_role_admin_gets_django_admin_access(self):
        u = User.objects.create_user(email='a@test.ru', username='a', full_name='A',
                                     password='Pass12345!', role='admin')
        self.assertTrue(u.is_staff and u.is_superuser)

    def test_superuser_gets_admin_role(self):
        u = User.objects.create_superuser(email='s@test.ru', username='s', full_name='S',
                                          password='Pass12345!')
        self.assertEqual(u.role, 'admin')

    def test_customer_stays_customer(self):
        u = User.objects.create_user(email='c@test.ru', username='c', full_name='C', password='Pass12345!')
        self.assertFalse(u.is_staff or u.is_superuser)
        self.assertEqual(u.role, 'customer')
