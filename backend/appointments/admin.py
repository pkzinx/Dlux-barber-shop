from django.contrib import admin
from .models import Appointment, TimeBlock, NotificationSubscription, AppointmentNotification, ClientToken


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'barber', 'service', 'start_datetime', 'end_datetime', 'status')
    list_filter = ('status', 'barber', 'service')
    search_fields = ('client_name', 'client_phone')
    date_hierarchy = 'start_datetime'

# Register your models here.

@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('barber', 'date', 'full_day', 'start_time', 'end_time', 'reason')
    list_filter = ('barber', 'date', 'full_day')


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'token', 'created_at')
    search_fields = ('token', 'appointment__client_name')
    list_filter = ('appointment__barber',)


@admin.register(AppointmentNotification)
class AppointmentNotificationAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'type', 'sent_at')
    list_filter = ('type', 'appointment__barber')


@admin.register(ClientToken)
class ClientTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'created_at', 'last_seen_at')
    search_fields = ('token',)
