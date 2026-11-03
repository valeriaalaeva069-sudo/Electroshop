from rest_framework import serializers


class DashboardStatsSerializer(serializers.Serializer):
    """Общая статистика для дашборда"""
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_products = serializers.IntegerField()
    orders_today = serializers.IntegerField()
    revenue_today = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()


class RevenueByPeriodSerializer(serializers.Serializer):
    """Выручка по периодам"""
    period = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    orders_count = serializers.IntegerField()


class TopProductSerializer(serializers.Serializer):
    """Популярный товар"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    category_name = serializers.CharField()
    total_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)


class OrderStatusStatsSerializer(serializers.Serializer):
    """Статистика по статусам заказов"""
    status_name = serializers.CharField()
    status_color = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class CategoryStatsSerializer(serializers.Serializer):
    """Статистика по категориям"""
    category_name = serializers.CharField()
    products_count = serializers.IntegerField()
    total_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)