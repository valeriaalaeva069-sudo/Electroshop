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
