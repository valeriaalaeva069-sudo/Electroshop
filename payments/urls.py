from django.urls import path
from . import views

urlpatterns = [
    path('payments/process/', views.ProcessPaymentView.as_view(), name='payment-process'),
]