from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import Category, Product

User = get_user_model()


class ProductVisibilityTests(APITestCase):
    def setUp(self):
        cat = Category.objects.create(name='Phones', slug='phones')
        self.active = Product.objects.create(
            name='A', slug='a', category=cat, price=1, stock_quantity=1, description='x')
        self.hidden = Product.objects.create(
            name='H', slug='h', category=cat, price=1, stock_quantity=1, description='x', is_active=False)

    def test_list_hides_inactive(self):
        r = self.client.get('/api/products/')
        slugs = [p['slug'] for p in r.data['results']]
        self.assertEqual(slugs, ['a'])

    def test_detail_of_inactive_is_404_for_guest(self):
        self.assertEqual(self.client.get('/api/products/h/').status_code, 404)
        self.assertEqual(self.client.get('/api/products/a/').status_code, 200)

    def test_admin_can_see_inactive(self):
        admin = User.objects.create_user(
            email='a@test.ru', username='adm', full_name='Adm', password='Pass12345!', role='admin')
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get('/api/products/h/').status_code, 200)
