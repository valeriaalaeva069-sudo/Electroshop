from django.urls import path
from . import views

urlpatterns = [
    path('analytics/dashboard/', views.DashboardStatsView.as_view(), name='analytics-dashboard'),
    path('analytics/revenue/', views.RevenueByPeriodView.as_view(), name='analytics-revenue'),
    path('analytics/top-products/', views.TopProductsView.as_view(), name='analytics-top-products'),
    path('analytics/order-statuses/', views.OrderStatusStatsView.as_view(), name='analytics-order-statuses'),
    path('analytics/categories/', views.CategoryStatsView.as_view(), name='analytics-categories'),
    path('analytics/export/excel/', views.ExportExcelView.as_view(), name='analytics-export-excel'),
    path('analytics/export/pdf/', views.ExportPdfView.as_view(), name='analytics-export-pdf'),
]