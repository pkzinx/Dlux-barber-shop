from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out

from .models import AuditLog
from appointments.models import Appointment
from sales.models import Sale


@receiver(pre_save, sender=Appointment)
def capture_appointment_original(sender, instance: Appointment, **kwargs):
    if getattr(instance, 'pk', None):
        try:
            orig = Appointment.objects.get(pk=instance.pk)
            instance._orig = {
                'status': orig.status,
                'start': orig.start_datetime,
                'end': orig.end_datetime,
                'service_id': getattr(orig.service, 'id', None),
                'service_title': getattr(orig.service, 'title', ''),
                'barber_id': getattr(orig.barber, 'id', None),
                'barber_label': (getattr(orig.barber, 'display_name', None) or getattr(orig.barber, 'username', None)),
            }
        except Exception:
            instance._orig = {}
    else:
        instance._orig = {}


@receiver(post_save, sender=Appointment)
def log_appointment_change(sender, instance: Appointment, created, **kwargs):
    payload_base = {
        'barber': instance.barber_id,
        'barber_label': (getattr(instance.barber, 'display_name', None) or getattr(instance.barber, 'username', None)),
        'client_name': instance.client_name,
        'start': instance.start_datetime.isoformat(),
        'end': instance.end_datetime.isoformat(),
        'status': instance.status,
        'service_id': getattr(getattr(instance, 'service', None), 'id', None),
        'service_title': getattr(getattr(instance, 'service', None), 'title', ''),
    }
    if created:
        AuditLog.objects.create(
            actor=getattr(instance, '_actor', None),
            action='create',
            target_type='Appointment',
            target_id=str(instance.pk),
            payload=payload_base,
        )
        return

    orig = getattr(instance, '_orig', {}) or {}
    status_changed = ('status' in orig) and (orig.get('status') != instance.status)
    time_changed = (
        ('start' in orig) and (orig.get('start') != instance.start_datetime)
    ) or (
        ('end' in orig) and (orig.get('end') != instance.end_datetime)
    )
    barber_changed = ('barber_id' in orig) and (orig.get('barber_id') != instance.barber_id)
    service_changed = ('service_id' in orig) and (orig.get('service_id') != getattr(getattr(instance, 'service', None), 'id', None))

    if not (status_changed or time_changed or barber_changed or service_changed):
        return

    if status_changed:
        change_type = 'cancel' if instance.status == 'cancelled' else ('done' if instance.status == 'done' else 'status_change')
    elif time_changed:
        change_type = 'reschedule'
    elif barber_changed:
        change_type = 'barber_change'
    else:
        change_type = 'service_change'

    payload = dict(payload_base)
    payload['change_type'] = change_type
    if status_changed:
        payload['old_status'] = orig.get('status')
    if time_changed:
        try:
            payload['old_start'] = orig.get('start').isoformat() if orig.get('start') else None
            payload['old_end'] = orig.get('end').isoformat() if orig.get('end') else None
        except Exception:
            payload['old_start'] = None
            payload['old_end'] = None
    if barber_changed:
        payload['old_barber'] = orig.get('barber_id')
        payload['old_barber_label'] = orig.get('barber_label')
    if service_changed:
        payload['old_service_id'] = orig.get('service_id')
        payload['old_service_title'] = orig.get('service_title')

    AuditLog.objects.create(
        actor=getattr(instance, '_actor', None),
        action='update',
        target_type='Appointment',
        target_id=str(instance.pk),
        payload=payload,
    )


@receiver(post_save, sender=Sale)
def log_sale_change(sender, instance: Sale, created, **kwargs):
    AuditLog.objects.create(
        actor=getattr(instance, '_actor', None),
        action='create' if created else 'update',
        target_type='Sale',
        target_id=str(instance.pk),
        payload={
            'barber': instance.barber_id,
            'barber_label': (getattr(instance.barber, 'display_name', None) or getattr(instance.barber, 'username', None)),
            'amount': str(instance.amount),
            'status': instance.status,
        }
    )


@receiver(user_logged_in)
def log_login(sender, user, request, **kwargs):
    AuditLog.objects.create(
        actor=user,
        action='login',
        target_type='User',
        target_id=str(user.pk),
        payload={'username': user.username}
    )


@receiver(user_logged_out)
def log_logout(sender, user, request, **kwargs):
    if user:
        AuditLog.objects.create(
            actor=user,
            action='logout',
            target_type='User',
            target_id=str(user.pk),
            payload={'username': user.username}
        )
