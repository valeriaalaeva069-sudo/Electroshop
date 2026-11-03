from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'status', 'payment_method', 'transaction_id', 'created_at']


class CardPaymentSerializer(serializers.Serializer):
    """Сериализатор для оплаты картой"""
    order_id = serializers.IntegerField()
    card_number = serializers.CharField(max_length=19)
    card_holder = serializers.CharField(max_length=100)
    expiry = serializers.CharField(max_length=5)
    cvv = serializers.CharField(max_length=4, write_only=True)

    def validate_card_number(self, value):
        # Убираем пробелы
        cleaned = value.replace(' ', '')
        if not cleaned.isdigit() or len(cleaned) != 16:
            raise serializers.ValidationError('Неверный номер карты')
        return cleaned

    def validate_expiry(self, value):
        if not value or '/' not in value:
            raise serializers.ValidationError('Формат: MM/YY')
        return value

    def validate_cvv(self, value):
        if not value.isdigit() or len(value) not in [3, 4]:
            raise serializers.ValidationError('Неверный CVV')
        return value