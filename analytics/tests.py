from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from orders.models import Order, OrderItem, OrderStatus
from products.models import Category, Product

User = get_user_model()


class AnalyticsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='a@test.ru', username='a', full_name='A', password='Pass12345!', role='admin')
        self.client.force_authenticate(self.admin)
        acc = Category.objects.create(name='Аксессуары', slug='accessories')
        mice = Category.objects.create(name='Мышки', slug='mice', parent=acc)
        self.mouse = Product.objects.create(
            name='Mouse', slug='mouse', category=mice, price=100, stock_quantity=10, description='x')

        def order(status_name, qty):
            o = Order.objects.create(
                user=self.admin, status=OrderStatus.objects.get(name=status_name),
                total_amount=100 * qty, city='М', address='а')
            OrderItem.objects.create(order=o, product=self.mouse, product_name='Mouse',
                                     price=Decimal('100'), quantity=qty)
        order('Оформлен', 2)
        order('Отменён', 5)  # не должен попасть в продажи

    def test_parent_category_includes_children_and_skips_cancelled(self):
        r = self.client.get('/api/analytics/categories/')
        self.assertEqual(r.status_code, 200)
        rows = {row['category_name']: row for row in r.data}
        self.assertEqual(rows['Аксессуары']['total_sold'], 2)
        self.assertEqual(rows['Аксессуары']['products_count'], 1)
        self.assertEqual(rows['↳ Мышки']['total_sold'], 2)

    def test_top_products_skip_cancelled(self):
        r = self.client.get('/api/analytics/top-products/?limit=5')
        self.assertEqual(r.data[0]['total_sold'], 2)

    def test_bad_params_give_400(self):
        for url in ['/api/analytics/top-products/?limit=abc',
                    '/api/analytics/dashboard/?period=custom&start_date=2026-13-45',
                    '/api/analytics/revenue/?period=custom&start_date=2026-10-20&end_date=2026-10-01',
                    '/api/analytics/export/excel/?start_date=nope&end_date=2026-10-01']:
            self.assertEqual(self.client.get(url).status_code, 400, url)

    def test_exports_work(self):
        for fmt in ['excel', 'pdf']:
            r = self.client.get(f'/api/analytics/export/{fmt}/?period=month')
            self.assertEqual(r.status_code, 200, fmt)
            self.assertGreater(len(b''.join(r.streaming_content)), 1000)

    def test_customer_has_no_access(self):
        u = User.objects.create_user(email='c@test.ru', username='c', full_name='C', password='Pass12345!')
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get('/api/analytics/dashboard/').status_code, 403)


class RevenuePeriodsTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(
            email='a@test.ru', username='a', full_name='A', password='Pass12345!', role='admin')
        self.client.force_authenticate(admin)

    def test_today_is_hourly(self):
        r = self.client.get('/api/analytics/revenue/?period=today')
        self.assertEqual(len(r.data), 24)
        self.assertEqual(r.data[0]['period'], '00:00')

    def test_week_and_month_lengths(self):
        self.assertEqual(len(self.client.get('/api/analytics/revenue/?period=week').data), 7)
        self.assertEqual(len(self.client.get('/api/analytics/revenue/?period=month').data), 30)

    def test_moscow_time_late_evening_order_goes_to_local_day(self):
        # 22:30 UTC 31-го = 01:30 МСК 1-го числа следующего месяца
        from datetime import datetime, timezone as dt_tz
        from analytics.utils import get_revenue_by_period
        from orders.models import Order, OrderStatus
        user = User.objects.get(email='a@test.ru')
        o = Order.objects.create(user=user, status=OrderStatus.objects.get(name='Оформлен'),
                                 total_amount=100, city='М', address='а')
        Order.objects.filter(pk=o.pk).update(created_at=datetime(2026, 9, 30, 22, 30, tzinfo=dt_tz.utc))
        from datetime import date
        data = get_revenue_by_period('custom', date(2026, 9, 30), date(2026, 10, 1))
        by_day = {row['period']: row['orders_count'] for row in data}
        self.assertEqual(by_day, {'30.09.2026': 0, '01.10.2026': 1})
