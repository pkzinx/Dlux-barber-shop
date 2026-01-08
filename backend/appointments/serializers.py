from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'barber', 'client_name', 'client_phone', 'service',
            'start_datetime', 'end_datetime', 'status', 'notes', 'created_at'
        ]
        extra_kwargs = {
            'notes': {'required': False, 'allow_blank': True}
        }
