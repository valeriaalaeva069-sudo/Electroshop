from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/receipt/', views.OrderReceiptView.as_view(), name='order-receipt'),
    path('orders/<int:pk>/status/', views.OrderUpdateStatusView.as_view(), name='order-update-status'),
    path('order-statuses/', views.OrderStatusListView.as_view(), name='order-status-list'),
]