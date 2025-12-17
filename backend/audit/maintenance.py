from django.db import transaction
from django.utils import timezone

from .models import MaintenanceRun, AuditLog
from appointments.models import Appointment, TimeBlock, NotificationSubscription, AppointmentNotification
from sales.models import Sale


def monthly_purge_if_due():
    today = timezone.localdate()
    if today.day != 5:
        return
    with transaction.atomic():
        mr, _ = MaintenanceRun.objects.select_for_update().get_or_create(name='monthly_purge')
        if mr.last_run_date and mr.last_run_date.year == today.year and mr.last_run_date.month == today.month:
            return

        cutoff_dt = timezone.now() - timezone.timedelta(days=90)
        cutoff_date = today - timezone.timedelta(days=90)

        Sale.objects.filter(created_at__lt=cutoff_dt).delete()
        Appointment.objects.filter(end_datetime__lt=cutoff_dt).delete()
        AuditLog.objects.filter(timestamp__lt=cutoff_dt).delete()
        TimeBlock.objects.filter(date__lt=cutoff_date).delete()
        NotificationSubscription.objects.filter(created_at__lt=cutoff_dt).delete()
        AppointmentNotification.objects.filter(sent_at__lt=cutoff_dt).delete()

        mr.last_run_date = today
        mr.save(update_fields=['last_run_date'])
