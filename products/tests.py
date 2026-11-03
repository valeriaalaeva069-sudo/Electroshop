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


class FacetsAndFiltersTests(APITestCase):
    def setUp(self):
        from products.models import Brand
        cat = Category.objects.create(name='Phones', slug='phones')
        a = Brand.objects.create(name='A', slug='a')
        b = Brand.objects.create(name='B', slug='b')
        Product.objects.create(name='p1', slug='p1', category=cat, brand=a, price=100, stock_quantity=1, description='x')
        Product.objects.create(name='p2', slug='p2', category=cat, brand=b, price=500, stock_quantity=0, description='x')

    def test_facets_have_brands_and_price_range(self):
        r = self.client.get('/api/products/facets/?category_slug=phones')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['brands']), 2)
        self.assertEqual(r.data['price'], {'min': 100, 'max': 500})

    def test_filter_by_several_brands_and_stock(self):
        r = self.client.get('/api/products/?brand_slug=a&brand_slug=b')
        self.assertEqual(r.data['count'], 2)
        r = self.client.get('/api/products/?brand_slug=a&brand_slug=b&in_stock=true')
        self.assertEqual(r.data['count'], 1)


class SeedDemoTests(APITestCase):
    def test_seed_demo_fills_empty_database(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_demo', stdout=StringIO())
        self.assertTrue(Category.objects.filter(slug='mice', parent__slug='accessories').exists())
        self.assertGreater(Product.objects.count(), 50)
        # повторный запуск ничего не ломает и не дублирует
        count = Product.objects.count()
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Product.objects.count(), count)


class BadQueryParamsTests(APITestCase):
    def test_bad_filters_give_400_not_500(self):
        for q in ['price_min=abc', 'price_max=-5', 'price_min=NaN', 'attr_color=abc']:
            self.assertEqual(self.client.get(f'/api/products/?{q}').status_code, 400, q)

    def test_good_filters_still_work(self):
        self.assertEqual(self.client.get('/api/products/?price_min=10&price_max=99.5').status_code, 200)
