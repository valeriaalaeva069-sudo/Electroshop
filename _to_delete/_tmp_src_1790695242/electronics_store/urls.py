from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .swagger import schema_view
from . import views

urlpatterns = [
    # HTML-страницы
    path('', views.index, name='index'),
    path('login/', views.login_page, name='login-page'),
    path('register/', views.register_page, name='register-page'),
    path('cart/', views.cart_page, name='cart-page'),
    path('checkout/', views.checkout_page, name='checkout-page'),
    path('orders/', views.orders_page, name='orders-page'),
    path('profile/', views.profile_page, name='profile-page'),
    path('product/<slug:slug>/', views.product_detail_page, name='product-page'),
    path('payment/<int:order_id>/', views.payment_page, name='payment-page'),
    path('order-success/<int:order_id>/', views.order_success_page, name='order-success'),
    path('password-reset/', views.password_reset_page, name='password-reset'),
    path('password-reset/confirm/', views.password_reset_confirm_page, name='password-reset-confirm'),
    path('admin-panel/', views.admin_panel, name='admin-panel'),

    # Django-админка
    path('admin/', admin.site.urls),

    # API
    path('api/', include('users.urls')),
    path('api/', include('products.urls')),
    path('api/', include('cart.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('analytics.urls')),
    path('api/', include('payments.urls')),

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)