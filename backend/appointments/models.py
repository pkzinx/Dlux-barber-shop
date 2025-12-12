from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User
from services.models import Service


class Appointment(models.Model):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Agendado'),
        (STATUS_DONE, 'Finalizado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    barber = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.BARBER}, related_name='appointments')
    client_name = models.CharField(max_length=120)
    client_phone = models.CharField(max_length=32)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['barber', 'start_datetime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.client_name} - {self.service.title} ({self.start_datetime:%d/%m %H:%M})"

    def clean(self):
        # calcular end_datetime se não fornecido
        if not self.end_datetime and self.service:
            self.end_datetime = self.start_datetime + timezone.timedelta(minutes=self.service.duration_minutes)

        
        if self.barber_id and self.start_datetime and self.end_datetime:
            qs = Appointment.objects.filter(barber=self.barber, status=self.STATUS_SCHEDULED)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            conflict = qs.filter(
                start_datetime__lt=(self.end_datetime + timezone.timedelta(minutes=5)),
                end_datetime__gt=(self.start_datetime - timezone.timedelta(minutes=5))
            ).exists()
            if conflict:
                raise ValidationError('Conflito de horário: barbeiro já possui agendamento nesse intervalo.')

            # validar conflito com bloqueios de horário (TimeBlock)
            try:
                from .models import TimeBlock  # local import para evitar ordem de definição
                # Converter para horário local para comparação por data
                start_local = timezone.localtime(self.start_datetime)
                end_local = timezone.localtime(self.end_datetime)
                day = start_local.date()
                blocks = TimeBlock.objects.filter(barber=self.barber, date=day)
                for b in blocks:
                    if b.full_day:
                        raise ValidationError('Conflito: barbeiro indisponível o dia inteiro.')
                    if b.start_time and b.end_time:
                        block_start = start_local.replace(hour=b.start_time.hour, minute=b.start_time.minute, second=0, microsecond=0)
                        block_end = start_local.replace(hour=b.end_time.hour, minute=b.end_time.minute, second=0, microsecond=0)
                        # Conflito se houver interseção
                        if block_start < end_local and block_end > start_local:
                            raise ValidationError('Conflito: intervalo bloqueado pelo barbeiro.')
            except Exception:
                # Em caso de erro inesperado, não bloquear o save, mas evitar quebra
                pass

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class TimeBlock(models.Model):
    """Bloqueio de horários para barbeiros (pausas, almoço, indisponibilidade).
    Se full_day=True, o barbeiro fica indisponível o dia inteiro.
    Caso contrário, usar start_time e end_time como intervalo dentro do dia.
    """
    barber = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.BARBER}, related_name='time_blocks')
    date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    full_day = models.BooleanField(default=False)
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['barber', 'date']),
        ]
        verbose_name = 'Bloqueio de horário'
        verbose_name_plural = 'Bloqueios de horário'

    def __str__(self):
        label = self.reason or 'Bloqueio'
        if self.full_day:
            return f"{label} - {self.date} (dia inteiro)"
        return f"{label} - {self.date} {self.start_time}–{self.end_time}"

    def clean(self):
        if not self.full_day:
            if not self.start_time or not self.end_time:
                raise ValidationError('Para bloqueios parciais, informe início e fim.')
            if self.start_time >= self.end_time:
                raise ValidationError('Horário de início deve ser antes do fim.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

# Create your models here.


class NotificationSubscription(models.Model):
    """Token de notificação push (FCM) vinculado a um agendamento específico.
    Um cliente pode ter múltiplos tokens (navegadores/dispositivos)."""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notification_subscriptions')
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['token']),
        ]
        unique_together = [('appointment', 'token')]

    def __str__(self):
        return f"Subscrição {self.appointment_id} - {self.token[:12]}..."


class AppointmentNotification(models.Model):
    """Registro de lembretes enviados para um agendamento (evita duplicidade)."""
    TYPE_GREETING_30 = 'greeting_30'
    TYPE_ALERT_10 = 'alert_10'
    TYPE_CHOICES = [
        (TYPE_GREETING_30, 'Saudação 30 min'),
        (TYPE_ALERT_10, 'Alerta 10 min'),
    ]

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['appointment', 'type']),
        ]
        unique_together = [('appointment', 'type')]

    def __str__(self):
        return f"Notificação {self.type} para appt #{self.appointment_id}"
