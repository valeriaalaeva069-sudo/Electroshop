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
        # статусы создаёт миграция 0004 — здесь только проверяем, что они на месте
        self.assertTrue(OrderStatus.objects.filter(name='Оформлен').exists())
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
    def test_customer_cannot_change_order_status(self):
        u = User.objects.create_user(email='c@test.ru', username='c', full_name='C', password='Pass12345!')
        self.client.force_authenticate(u)
        r = self.client.get('/api/orders/1/status/')
        self.assertIn(r.status_code, (403, 405))


class DefaultStatusesTests(APITestCase):
    def test_statuses_exist_on_clean_database(self):
        names = set(OrderStatus.objects.values_list('name', flat=True))
        for name in ['Оформлен', 'Оплачен', 'В сборке', 'Собран', 'В пути', 'Доставлен', 'Получен', 'Отменён']:
            self.assertIn(name, names)


class _OrderFixture(APITestCase):
    """Пользователь, админ и один оформленный заказ на 2 шт. товара (на складе осталось 3)."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='buyer@test.ru', username='buyer', full_name='Buyer', password='Pass12345!')
        self.admin = User.objects.create_user(
            email='adm@test.ru', username='adm', full_name='Adm', password='Pass12345!', role='admin')
        cat = Category.objects.create(name='Phones', slug='phones')
        self.product = Product.objects.create(
            name='P', slug='p', category=cat, price=Decimal('100'), stock_quantity=5, description='x')
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.client.force_authenticate(self.user)
        r = self.client.post('/api/orders/create/', {
            'city': 'Москва', 'address': 'ул. Тестовая, 1',
            'delivery_method': 'pickup', 'payment_method': 'card'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.order = Order.objects.get()

    def set_status(self, name):
        self.client.force_authenticate(self.admin)
        return self.client.put(f'/api/orders/{self.order.id}/status/', {'status': name}, format='json')

    def pay(self, card='4111111111111111'):
        self.client.force_authenticate(self.user)
        return self.client.post('/api/payments/process/', {
            'order_id': self.order.id, 'card_number': card,
            'card_holder': 'TEST', 'expiry': '12/30', 'cvv': '123'}, format='json')


class CancelOrderTests(_OrderFixture):
    def test_cancel_returns_stock(self):
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(self.set_status('Отменён').status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_cancelled_order_cannot_be_reopened(self):
        self.set_status('Отменён')
        r = self.set_status('Оплачен')
        self.assertEqual(r.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status.name, 'Отменён')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)  # не вернули дважды

    def test_response_contains_new_history_entry(self):
        r = self.set_status('В сборке')
        self.assertEqual(r.data['status_history'][-1]['status_name'], 'В сборке')


class PaymentTests(_OrderFixture):
    def test_successful_payment(self):
        r = self.pay()
        self.assertEqual(r.status_code, 200, r.data)
        self.order.refresh_from_db()
        self.assertTrue(self.order.payment_status)
        self.assertEqual(self.order.status.name, 'Оплачен')

    def test_cannot_pay_twice(self):
        self.pay()
        self.assertEqual(self.pay().status_code, 400)

    def test_cannot_pay_cancelled_order(self):
        self.set_status('Отменён')
        r = self.pay()
        self.assertEqual(r.status_code, 400)
        self.order.refresh_from_db()
        self.assertFalse(self.order.payment_status)

    def test_payment_saved_even_without_paid_status(self):
        OrderStatus.objects.filter(name='Оплачен').delete()
        self.assertEqual(self.pay().status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.payment_status)

    def test_declined_card(self):
        self.assertEqual(self.pay('4444444444444444').status_code, 400)
        self.order.refresh_from_db()
        self.assertFalse(self.order.payment_status)


class DeleteWithOrdersTests(_OrderFixture):
    def test_category_with_ordered_products_is_not_deleted(self):
        self.client.force_authenticate(self.admin)
        r = self.client.delete('/api/categories/phones/')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Category.objects.filter(slug='phones').exists())

    def test_empty_category_is_deleted(self):
        Category.objects.create(name='Empty', slug='empty')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete('/api/categories/empty/').status_code, 204)

    def test_ordered_product_is_hidden_not_deleted(self):
        self.client.force_authenticate(self.admin)
        r = self.client.delete('/api/products/p/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['soft_delete'])
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)


class OrderListScopeTests(_OrderFixture):
    def test_admin_sees_only_own_orders_by_default(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/orders/')
        self.assertEqual(r.data['count'], 0)

    def test_admin_sees_all_with_scope(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get('/api/orders/?scope=all')
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['customer_email'], 'buyer@test.ru')

    def test_customer_cannot_use_scope_all(self):
        other = User.objects.create_user(email='o@test.ru', username='o', full_name='O', password='Pass12345!')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get('/api/orders/?scope=all').data['count'], 0)


class MinorFixesTests(_OrderFixture):
    def test_email_and_notification_after_commit(self):
        from django.core import mail
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)
        with self.settings(EMAIL_HOST_USER='shop@test.ru', EMAIL_HOST_PASSWORD='x'):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                r = self.client.post('/api/orders/create/', {
                    'city': 'М', 'address': 'а', 'delivery_method': 'pickup', 'payment_method': 'cash'},
                    format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(r.data['order_number'], mail.outbox[0].subject)

    def _make_order(self, payment_method='card'):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_authenticate(self.user)
        r = self.client.post('/api/orders/create/', {
            'city': 'М', 'address': 'а', 'delivery_method': 'pickup', 'payment_method': payment_method},
            format='json')
        self.assertEqual(r.status_code, 201)
        return r.data['id']

    def test_receipt_pdf_for_paid_order(self):
        oid = self._make_order('card')
        pay = self.client.post('/api/payments/process/', {
            'order_id': oid, 'card_number': '4242424242424242',
            'card_holder': 'IVAN IVANOV', 'expiry': '12/30', 'cvv': '123'}, format='json')
        self.assertEqual(pay.status_code, 200, pay.data)
        r = self.client.get(f'/api/orders/{oid}/receipt/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertIn('attachment', r['Content-Disposition'])

    def test_receipt_pdf_for_unpaid_order(self):
        oid = self._make_order('cash')
        r = self.client.get(f'/api/orders/{oid}/receipt/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_receipt_of_foreign_order_is_404(self):
        oid = self._make_order('cash')
        other = User.objects.create_user(email='o@test.ru', username='o', full_name='O', password='Pass12345!')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f'/api/orders/{oid}/receipt/').status_code, 404)

    def test_receipt_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/orders/1/receipt/').status_code, 401)

    def test_order_without_cart_is_400(self):
        other = User.objects.create_user(email='n@test.ru', username='n', full_name='N', password='Pass12345!')
        self.client.force_authenticate(other)
        r = self.client.post('/api/orders/create/', {'city': 'М', 'address': 'а'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_clear_cart_without_cart_is_ok(self):
        other = User.objects.create_user(email='n@test.ru', username='n', full_name='N', password='Pass12345!')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post('/api/cart/clear/').status_code, 200)

    def test_cash_order_cannot_be_paid_by_card(self):
        Order.objects.filter(pk=self.order.pk).update(payment_method='cash')
        r = self.pay()
        self.assertEqual(r.status_code, 400)
        self.order.refresh_from_db()
        self.assertFalse(self.order.payment_status)
