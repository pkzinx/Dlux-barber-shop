from rest_framework import serializers
from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['id', 'barber', 'appointment', 'service', 'description', 'amount', 'payment_method', 'status', 'created_at']
        extra_kwargs = {
            'payment_method': {'required': False},
            'appointment': {'required': False},
            'service': {'required': False},
            'status': {'required': False},
        }

    def create(self, validated_data):
        if 'payment_method' not in validated_data or not validated_data.get('payment_method'):
            validated_data['payment_method'] = 'cash'
        if 'status' not in validated_data or not validated_data.get('status'):
            validated_data['status'] = 'paid'
        return super().create(validated_data)
