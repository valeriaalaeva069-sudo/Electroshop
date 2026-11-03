from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.CartDetailView.as_view(), name='cart-detail'),
    path('cart/add/', views.CartAddItemView.as_view(), name='cart-add'),
    path('cart/items/<int:pk>/', views.CartUpdateItemView.as_view(), name='cart-update-item'),
    path('cart/items/<int:pk>/remove/', views.CartRemoveItemView.as_view(), name='cart-remove-item'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart-clear'),
]