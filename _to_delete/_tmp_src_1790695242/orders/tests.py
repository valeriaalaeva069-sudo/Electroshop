from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from cart.models import Cart, CartItem
from orders.models import Order, OrderStatus
from products.models import Category, Product

User = get_user_model()


class OrderCreateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='buyer@test.ru', username='buyer', full_name='Buyer', password='Pass12345!')
        self.client.force_authenticate(self.user)
        OrderStatus.objects.create(name='Оформлен', order=1)
        self.cat = Category.objects.create(name='Phones', slug='phones')

    def _product(self, slug, price, stock, active=True):
        return Product.objects.create(
            name=slug, slug=slug, category=self.cat, price=price,
            stock_quantity=stock, description='x', is_active=active)

    def _fill_cart(self, product, qty):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=product, quantity=qty)

    def _order(self, method='courier', **extra):
        data = {'city': 'Москва', 'address': 'ул. Тестовая, 1',
                'delivery_method': method, 'payment_method': 'cash'}
        data.update(extra)
        return self.client.post('/api/orders/create/', data, format='json')

    def test_delivery_cost_is_computed_on_server(self):
        p = self._product('cheap', Decimal('1000'), 5)
        self._fill_cart(p, 1)
        # клиент пытается подставить нулевую доставку — сервер должен проигнорировать
        r = self._order('courier', delivery_cost='0')
        self.assertEqual(r.status_code, 201, r.data)
        order = Order.objects.get()
        self.assertEqual(order.delivery_cost, Decimal('500'))
        self.assertEqual(order.total_amount, Decimal('1500'))

    def test_free_courier_from_10000_and_pickup_is_free(self):
        p = self._product('pricey', Decimal('10000'), 5)
        self._fill_cart(p, 1)
        self._order('courier')
        self.assertEqual(Order.objects.get().delivery_cost, Decimal('0'))

    def test_stock_is_decreased(self):
        p = self._product('stock', Decimal('100'), 5)
        self._fill_cart(p, 2)
        self.assertEqual(self._order('pickup').status_code, 201)
        p.refresh_from_db()
        self.assertEqual(p.stock_quantity, 3)

    def test_not_enough_stock(self):
        p = self._product('few', Decimal('100'), 1)
        self._fill_cart(p, 2)
        self.assertEqual(self._order('pickup').status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_inactive_product_cannot_be_ordered(self):
        p = self._product('hidden', Decimal('100'), 5, active=False)
        self._fill_cart(p, 1)
        self.assertEqual(self._order('pickup').status_code, 400)

    def test_order_numbers_are_unique(self):
        p = self._product('multi', Decimal('100'), 10)
        for _ in range(3):
            self._fill_cart(p, 1)
            self.assertEqual(self._order('pickup').status_code, 201)
            CartItem.objects.all().delete()
        self.assertEqual(Order.objects.values('order_number').distinct().count(), 3)

    def test_order_detail_has_status_history(self):
        p = self._product('hist', Decimal('100'), 5)
        self._fill_cart(p, 1)
        oid = self._order('pickup').data['id']
        r = self.client.get(f'/api/orders/{oid}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['status_history']), 1)


class AdminPermissionTests(APITestCase):
    def test_customer_cannot_open_analytics(self):
        u = User.objects.create_user(email='c@test.ru', username='c', full_name='C', password='Pass12345!')
        self.client.force_authenticate(u)
        r = self.client.get('/api/orders/1/status/')
        self.assertIn(r.status_code, (403, 405))
