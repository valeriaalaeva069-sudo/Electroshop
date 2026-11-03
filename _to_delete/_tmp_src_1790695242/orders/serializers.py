from rest_framework import serializers
from .models import Order, OrderItem, OrderStatus, OrderStatusHistory


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['id', 'name', 'color', 'icon', 'order', 'is_active']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'price', 'quantity']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True, default='Система')

    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'status_name', 'status_color', 'comment', 'changed_by_name', 'changed_at']


class OrderSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.name', read_only=True)
    status_color = serializers.CharField(source='status.color', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_name', 'status_color',
            'total_amount', 'delivery_cost', 'city', 'address',
            'delivery_method', 'payment_method', 'payment_status',
            'tracking_number', 'comment', 'created_at', 'updated_at',
            'items_count'
        ]

    def get_items_count(self, obj):
        return len(obj.items.all())


class OrderDetailSerializer(OrderSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True, source='status_history_entries')

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['items', 'status_history']


class OrderCreateSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=100)
    address = serializers.CharField()
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    delivery_method = serializers.ChoiceField(choices=Order.DELIVERY_CHOICES, default='courier')
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES, default='card')
    delivery_cost = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    comment = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="ID позиций корзины"
    )