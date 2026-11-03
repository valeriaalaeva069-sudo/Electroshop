from rest_framework.test import APITestCase

from products.models import Category, Product


class GuestCartTests(APITestCase):
    """Гость может смотреть товары, но не может пользоваться корзиной."""

    def setUp(self):
        cat = Category.objects.create(name='Phones', slug='phones')
        self.product = Product.objects.create(
            name='P', slug='p', category=cat, price=100, stock_quantity=5, description='x')

    def test_guest_can_view_products(self):
        self.assertEqual(self.client.get('/api/products/').status_code, 200)
        self.assertEqual(self.client.get('/api/products/p/').status_code, 200)

    def test_guest_cannot_use_cart(self):
        self.assertEqual(self.client.get('/api/cart/').status_code, 401)
        r = self.client.post('/api/cart/add/', {'product_id': self.product.id, 'quantity': 1}, format='json')
        self.assertEqual(r.status_code, 401)
