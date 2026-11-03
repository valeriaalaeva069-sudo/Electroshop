from django.urls import path
from . import views

urlpatterns = [
    # Категории
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<slug:slug>/filters/', views.CategoryFiltersView.as_view(), name='category-filters'),

    # Бренды
    path('brands/', views.BrandListView.as_view(), name='brand-list'),
    path('brands/<slug:slug>/', views.BrandDetailView.as_view(), name='brand-detail'),

    # Товары
    path('products/facets/', views.ProductFacetsView.as_view(), name='product-facets'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),

    # Админские маршруты
    path('admin/products/', views.AdminProductListView.as_view(), name='admin-product-list'),
    path('admin/products/<int:pk>/', views.AdminProductDetailView.as_view(), name='admin-product-detail'),
    path('admin/categories/', views.AdminCategoryListView.as_view(), name='admin-category-list'),
    path('admin/brands/', views.AdminBrandListView.as_view(), name='admin-brand-list'),
]
