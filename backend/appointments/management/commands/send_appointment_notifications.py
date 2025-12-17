from django.core.management.base import BaseCommand
from django.utils import timezone
from appointments.models import Appointment, NotificationSubscription, AppointmentNotification
from appointments.fcm import send_push
import datetime


class Command(BaseCommand):
    help = 'Envio de notificações push para agendamentos: Confirmação, 30 min, 15 min, Na hora.'

    def handle(self, *args, **options):
        now = timezone.now()
        # Janela de 1 min para capturar eventos, assumindo execução frequente
        
        # 0. Confirmação (30s após criação)
        # Buscar agendamentos criados entre 30s e 5 min atrás (margem de segurança)
        # e que AINDA NÃO tenham recebido notificação de confirmação.
        confirm_threshold = now - datetime.timedelta(seconds=30)
        confirm_limit = now - datetime.timedelta(minutes=5)
        
        appts_confirm = Appointment.objects.filter(
            status=Appointment.STATUS_SCHEDULED,
            created_at__lte=confirm_threshold,
            created_at__gte=confirm_limit
        )

        # Janelas de tempo para lembretes
        # Usamos uma janela de 1 minuto para frente para pegar o momento exato
        # Execução recomendada: a cada 1 minuto (cron ou loop)
        
        # 30 minutos antes
        window_30_start = now + datetime.timedelta(minutes=30)
        window_30_end = now + datetime.timedelta(minutes=31)
        
        # 15 minutos antes
        window_15_start = now + datetime.timedelta(minutes=15)
        window_15_end = now + datetime.timedelta(minutes=16)

        # Na hora (0 a 1 min antes)
        window_0_start = now
        window_0_end = now + datetime.timedelta(minutes=1)

        # Queries
        appts_30 = Appointment.objects.filter(
            status=Appointment.STATUS_SCHEDULED,
            start_datetime__gte=window_30_start,
            start_datetime__lt=window_30_end,
        )
        appts_15 = Appointment.objects.filter(
            status=Appointment.STATUS_SCHEDULED,
            start_datetime__gte=window_15_start,
            start_datetime__lt=window_15_end,
        )
        appts_0 = Appointment.objects.filter(
            status=Appointment.STATUS_SCHEDULED,
            start_datetime__gte=window_0_start,
            start_datetime__lt=window_0_end,
        )

        sent_count = 0

        # --- PROCESSAMENTO CONFIRMAÇÃO ---
        for appt in appts_confirm:
            if AppointmentNotification.objects.filter(appointment=appt, type=AppointmentNotification.TYPE_CONFIRMATION).exists():
                continue
            subs = NotificationSubscription.objects.filter(appointment=appt)
            if not subs.exists():
                continue
            
            barber_name = getattr(appt.barber, 'display_name', None) or getattr(appt.barber, 'username', '')
            service_title = getattr(appt.service, 'title', '')
            start_local = timezone.localtime(appt.start_datetime).strftime('%d/%m às %H:%M')
            
            title = '✅ Agendamento Confirmado!'
            body = f'Tudo certo! Seu horário para {service_title} com {barber_name} está confirmado para {start_local}.'
            data = {'type': 'confirmation', 'appointmentId': str(appt.id)}
            
            any_sent = False
            for s in subs:
                if send_push(s.token, title, body, data):
                    any_sent = True
            
            if any_sent:
                AppointmentNotification.objects.create(appointment=appt, type=AppointmentNotification.TYPE_CONFIRMATION)
                sent_count += 1

        # --- PROCESSAMENTO 30 MIN ---
        for appt in appts_30:
            if AppointmentNotification.objects.filter(appointment=appt, type=AppointmentNotification.TYPE_GREETING_30).exists():
                continue
            subs = NotificationSubscription.objects.filter(appointment=appt)
            if not subs.exists():
                continue
                
            barber_name = getattr(appt.barber, 'display_name', None) or getattr(appt.barber, 'username', '')
            service_title = getattr(appt.service, 'title', '')
            start_local = timezone.localtime(appt.start_datetime).strftime('%H:%M')
            
            title = f'Lembrete: {service_title} às {start_local}'
            body = f'Olá! {barber_name} te espera para {service_title} em 30 minutos.'
            data = {'type': 'greeting_30', 'appointmentId': str(appt.id), 'service': service_title}
            
            any_sent = False
            for s in subs:
                if send_push(s.token, title, body, data):
                    any_sent = True
            
            if any_sent:
                AppointmentNotification.objects.create(appointment=appt, type=AppointmentNotification.TYPE_GREETING_30)
                sent_count += 1

        # --- PROCESSAMENTO 15 MIN ---
        for appt in appts_15:
            if AppointmentNotification.objects.filter(appointment=appt, type=AppointmentNotification.TYPE_ALERT_15).exists():
                continue
            subs = NotificationSubscription.objects.filter(appointment=appt)
            if not subs.exists():
                continue

            barber_name = getattr(appt.barber, 'display_name', None) or getattr(appt.barber, 'username', '')
            service_title = getattr(appt.service, 'title', '')
            
            title = f'⏰ 15 minutos para seu corte!'
            body = f'Seu horário com {barber_name} é daqui a pouco. Estamos te aguardando!'
            data = {'type': 'alert_15', 'appointmentId': str(appt.id), 'service': service_title}
            
            any_sent = False
            for s in subs:
                if send_push(s.token, title, body, data):
                    any_sent = True
            
            if any_sent:
                AppointmentNotification.objects.create(appointment=appt, type=AppointmentNotification.TYPE_ALERT_15)
                sent_count += 1

        # --- PROCESSAMENTO NA HORA (0 MIN) ---
        for appt in appts_0:
            if AppointmentNotification.objects.filter(appointment=appt, type=AppointmentNotification.TYPE_ALERT_0).exists():
                continue
            subs = NotificationSubscription.objects.filter(appointment=appt)
            if not subs.exists():
                continue

            barber_name = getattr(appt.barber, 'display_name', None) or getattr(appt.barber, 'username', '')
            service_title = getattr(appt.service, 'title', '')
            
            title = f'✂️ Chegou a hora!'
            body = f'Seu horário para {service_title} com {barber_name} é agora. Bom corte!'
            data = {'type': 'alert_0', 'appointmentId': str(appt.id), 'service': service_title}
            
            any_sent = False
            for s in subs:
                if send_push(s.token, title, body, data):
                    any_sent = True
            
            if any_sent:
                AppointmentNotification.objects.create(appointment=appt, type=AppointmentNotification.TYPE_ALERT_0)
                sent_count += 1

        if sent_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Notificações enviadas: {sent_count}'))
