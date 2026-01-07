from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, authentication_classes
from rest_framework.views import APIView
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Appointment
from .models import TimeBlock
from .models import NotificationSubscription, AppointmentNotification, ClientToken
from services.models import Service
from django.db.models import Q
from .serializers import AppointmentSerializer
from sales.models import Sale
from users.models import User
from decimal import Decimal
from django.utils.text import slugify
from django.utils import timezone
import datetime


class IsAdminOrOwnRecords(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj: Appointment):
        # Permitir administradores e usuários especiais (Kaue/Alafy variações) editar qualquer registro
        uname = (getattr(request.user, 'username', '') or '').lower()
        special_all_edit = uname in ['kaue', 'alafy', 'alafi', 'alefi']
        if request.user.role == User.ADMIN or special_all_edit:
            return True
        return obj.barber_id == request.user.id


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('start_datetime')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdminOrOwnRecords]

    def get_queryset(self):
        qs = super().get_queryset()
        # Importante: para rotas de detalhe (com pk), não aplique filtro por barbeiro aqui.
        # Isso evita 404 indevido ao buscar um objeto existente que não está no queryset filtrado.
        # A checagem de permissão por objeto continuará garantindo acesso correto.
        if 'pk' in getattr(self, 'kwargs', {}):
            return qs

        user = self.request.user
        barber_id = self.request.query_params.get('barberId')
        all_param = str(self.request.query_params.get('all') or '').lower() in ('1', 'true', 'on', 'yes')
        if not all_param:
            if user.role == User.BARBER:
                qs = qs.filter(barber=user)
            elif barber_id:
                qs = qs.filter(barber_id=barber_id)
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(start_datetime__date=date)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        start_param = self.request.query_params.get('start')
        end_param = self.request.query_params.get('end')
        tz = timezone.get_current_timezone()
        if start_param:
            try:
                d = datetime.date.fromisoformat(start_param)
                start_local = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
                start_local = timezone.make_aware(start_local, tz)
                start_utc = start_local.astimezone(datetime.timezone.utc)
                qs = qs.filter(start_datetime__gte=start_utc)
            except ValueError:
                pass
        if end_param:
            try:
                d = datetime.date.fromisoformat(end_param)
                # usar limite exclusivo: próximo dia às 00:00
                next_day = d + datetime.timedelta(days=1)
                end_local = datetime.datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0)
                end_local = timezone.make_aware(end_local, tz)
                end_utc = end_local.astimezone(datetime.timezone.utc)
                qs = qs.filter(start_datetime__lt=end_utc)
            except ValueError:
                pass
        future_param = self.request.query_params.get('future')
        if str(future_param).lower() in ('1', 'true', 'on', 'yes'):
            qs = qs.filter(end_datetime__gte=timezone.now())
        return qs

    def perform_create(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        """Atualiza parcialmente e registra o ator; se status=cancelled, cancela vendas."""
        appt = self.get_object()
        # Registrar quem realizou a edição para os sinais de auditoria
        setattr(appt, '_actor', request.user)
        serializer = self.get_serializer(appt, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        resp = Response(serializer.data)
        try:
            new_status = request.data.get('status')
            if new_status == Appointment.STATUS_CANCELLED:
                Sale.objects.filter(appointment=appt).update(status='cancelled')
        except Exception:
            # Evitar quebrar a resposta do update por erro secundário
            pass
        return resp

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        appt = self.get_object()
        # Registrar o ator que realizou a mudança de status
        setattr(appt, '_actor', request.user)
        status = request.data.get('status')
        if status not in dict(Appointment.STATUS_CHOICES):
            return Response({'detail': 'Status inválido.'}, status=400)
        appt.status = status
        appt.save()
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='subscribe', permission_classes=[permissions.AllowAny], authentication_classes=[])
    def subscribe(self, request, pk=None):
        """Recebe token FCM para um agendamento e salva subscrição.
        Body: { token: string }
        """
        appt = self.get_object()
        token = request.data.get('token') or request.data.get('fcmToken')
        if not token or not isinstance(token, str):
            return Response({'detail': 'Token FCM é obrigatório.'}, status=400)
        
        # Salvar token globalmente para promoções
        ClientToken.objects.update_or_create(token=token, defaults={'last_seen_at': timezone.now()})

        try:
            sub, created = NotificationSubscription.objects.get_or_create(appointment=appt, token=token)
            return Response({'ok': True, 'created': created})
        except Exception as e:
            return Response({'detail': str(e)}, status=400)

    @action(detail=True, methods=['post'], url_path='notify_test', permission_classes=[permissions.AllowAny], authentication_classes=[])
    def notify_test(self, request, pk=None):
        """Envia uma notificação de teste para todos os tokens inscritos no agendamento.
        Body opcional: { title?: string, body?: string, data?: object }
        """
        appt = self.get_object()
        title = request.data.get('title') or 'Teste de notificação'
        body = request.data.get('body') or 'Push de teste enviado com sucesso.'
        data = request.data.get('data')
        if not isinstance(data, dict):
            data = {}
        subs = NotificationSubscription.objects.filter(appointment=appt)
        total = subs.count()
        if total == 0:
            return Response({'ok': False, 'detail': 'Nenhum token inscrito para este agendamento.'}, status=404)
        # Import atrasado para evitar overhead quando não usado
        try:
            from .fcm import send_push
        except Exception:
            return Response({'ok': False, 'detail': 'FCM não configurado no servidor.'}, status=500)
        sent = 0
        for s in subs:
            try:
                if send_push(s.token, title, body, data):
                    sent += 1
            except Exception:
                pass
        return Response({'ok': True, 'sent': sent, 'total': total})

    @action(detail=False, methods=['get'], url_path='barbers')
    def list_barbers(self, request):
        """Lista barbeiros disponíveis para seleção no agendamento rápido."""
        barbers = User.objects.filter(role=User.BARBER).order_by('display_name', 'username')
        data = [
            {
                'id': b.id,
                'name': (b.display_name or b.username),
            }
            for b in barbers
        ]
        return Response({'barbers': data})

    @action(detail=False, methods=['get'], url_path='available-slots', permission_classes=[permissions.AllowAny], authentication_classes=[])
    def available_slots(self, request):
        """Retorna horários disponíveis (HH:MM) para um barbeiro em uma data.
        Considera a duração do serviço para que o próximo horário só apareça após o término.
        Query params:
        - barberId (opcional; padrão: usuário atual se barbeiro)
        - date (YYYY-MM-DD)
        - serviceId (opcional)
        - durationMinutes (opcional; usado se serviceId ausente)
        """
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'detail': 'Parâmetro "date" é obrigatório (YYYY-MM-DD).'}, status=400)

        try:
            day = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Data inválida.'}, status=400)

        barber_id = request.query_params.get('barberId')
        user = request.user
        if not barber_id and getattr(user, 'role', None) == User.BARBER:
            barber_id = user.id
        if not barber_id:
            # Tentar resolver por nome do barbeiro (display_name ou username)
            barber_name = request.query_params.get('barberName')
            if barber_name:
                candidate = User.objects.filter(role=User.BARBER).filter(Q(username__iexact=barber_name) | Q(display_name__iexact=barber_name)).first()
                if candidate:
                    barber_id = candidate.id
            if not barber_id:
                return Response({'detail': 'Parâmetro "barberId" ou "barberName" é obrigatório.'}, status=400)

        # Determinar duração
        duration_minutes = None
        service_id = request.query_params.get('serviceId')
        if service_id:
            svc = Service.objects.filter(pk=service_id).first()
            duration_minutes = getattr(svc, 'duration_minutes', None)
        if duration_minutes is None:
            dm = request.query_params.get('durationMinutes')
            if dm:
                try:
                    duration_minutes = int(dm)
                except ValueError:
                    return Response({'detail': 'durationMinutes inválido.'}, status=400)
        if not duration_minutes or duration_minutes <= 0:
            return Response({'detail': 'Duração do serviço é obrigatória.'}, status=400)

        tz = timezone.get_current_timezone()
        # Janela padrão de funcionamento: 08:00 às 20:00 (ajuste se necessário)
        window_start_naive = datetime.datetime.combine(day, datetime.time(8, 0))
        window_end_naive = datetime.datetime.combine(day, datetime.time(20, 0))
        window_start = timezone.make_aware(window_start_naive, tz)
        window_end = timezone.make_aware(window_end_naive, tz)

        # Se for hoje, não ofertar horários no passado (arredonda para próximo múltiplo de 10 min)
        now_local = timezone.localtime()
        if day == now_local.date():
            # Arredondar para cima para próximo múltiplo de 10 minutos
            minutes = (now_local.minute + 9) // 10 * 10
            now_rounded = now_local.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(minutes=minutes)
            if now_rounded > window_start:
                window_start = now_rounded

        # Buscar agendamentos existentes do barbeiro que sobrepõem a janela (excluir apenas cancelados)
        existing = Appointment.objects.filter(
            barber_id=barber_id,
            start_datetime__lt=window_end,
            end_datetime__gt=window_start,
        ).exclude(status=Appointment.STATUS_CANCELLED).values('start_datetime', 'end_datetime')

        # Buscar bloqueios de horário do barbeiro para o dia
        blocks = TimeBlock.objects.filter(barber_id=barber_id, date=day)
        # Se houver bloqueio de dia inteiro, não há slots disponíveis
        if blocks.filter(full_day=True).exists():
            return Response({'slots': []})

        # Gera slots a cada 10 minutos, garantindo que [start, end) não sobreponha existentes nem bloqueios
        step = datetime.timedelta(minutes=10)
        duration = datetime.timedelta(minutes=duration_minutes)
        slots = []
        cur = window_start
        # Para otimizar, prepara lista de ranges
        ranges = [(timezone.localtime(r['start_datetime']), timezone.localtime(r['end_datetime'])) for r in existing]
        # Adicionar ranges de bloqueio
        tz = timezone.get_current_timezone()
        for b in blocks:
            if not b.full_day and b.start_time and b.end_time:
                bs_naive = datetime.datetime.combine(day, b.start_time)
                be_naive = datetime.datetime.combine(day, b.end_time)
                bs = timezone.make_aware(bs_naive, tz)
                be = timezone.make_aware(be_naive, tz)
                ranges.append((timezone.localtime(bs), timezone.localtime(be)))
        while cur + duration <= window_end:
            proposed_start = cur
            proposed_end = cur + duration
            buf = datetime.timedelta(minutes=5)
            conflict = any((rs - buf) < proposed_end and (re + buf) > proposed_start for rs, re in ranges)
            if not conflict:
                slots.append(proposed_start.strftime('%H:%M'))
            cur += step

        return Response({'slots': slots})


@method_decorator(csrf_exempt, name='dispatch')
class PublicAppointmentCreate(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data
        # Basic validation: ensure barber exists and is a barber
        barber_id = data.get('barber') or data.get('barberId')
        service_id = data.get('service') or data.get('serviceId')

        # Permitir resolução por nome/username do barbeiro
        if not barber_id:
            barber_name = data.get('barber_name') or data.get('barberName') or data.get('barberUsername')
            if barber_name:
                candidate = User.objects.filter(role=User.BARBER).filter(Q(username__iexact=barber_name) | Q(display_name__iexact=barber_name)).first()
                if candidate:
                    barber_id = candidate.id
                else:
                    return Response({'detail': 'Barbeiro não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)

        # Permitir resolução por título do serviço
        if not service_id:
            service_title = data.get('service_title') or data.get('serviceTitle')
            if service_title:
                svc = Service.objects.filter(title__iexact=service_title).first()
                if svc:
                    service_id = svc.id
                else:
                    return Response({'detail': 'Serviço não encontrado.'}, status=status.HTTP_400_BAD_REQUEST)

        if not barber_id or not service_id:
            return Response({'detail': 'Barbeiro e serviço são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            barber = User.objects.get(pk=barber_id, role=User.BARBER)
        except User.DoesNotExist:
            return Response({'detail': 'Barbeiro inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Normalizar datetime: aceitar start_datetime/end_datetime prontos
        # ou construir a partir de date/time e calcular fim pela duração do serviço
        start_dt = data.get('start_datetime') or data.get('startDatetime')
        end_dt = data.get('end_datetime') or data.get('endDatetime')
        if not start_dt:
            date_str = data.get('date') or data.get('start_date') or data.get('startDate')
            time_str = data.get('time') or data.get('start_time') or data.get('startTime')
            if not date_str or not time_str:
                return Response({'detail': 'Data e horário são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                # Construir aware datetime no timezone atual
                tz = timezone.get_current_timezone()
                y, m, d = [int(x) for x in date_str.split('-')]
                hh, mm = [int(x) for x in time_str.split(':')[:2]]
                naive = datetime.datetime(y, m, d, hh, mm, 0)
                start_aware = timezone.make_aware(naive, tz)
                start_dt = start_aware.isoformat(timespec='seconds')
            except Exception:
                return Response({'detail': 'Data/horário inválidos.'}, status=status.HTTP_400_BAD_REQUEST)
        if not end_dt:
            try:
                svc = Service.objects.filter(pk=service_id).first()
                duration_minutes = getattr(svc, 'duration_minutes', None) or 30
                # Parse start_dt (aceita offset ISO 8601)
                try:
                    start_parsed = datetime.datetime.fromisoformat(str(start_dt))
                except Exception:
                    return Response({'detail': 'Início inválido.'}, status=status.HTTP_400_BAD_REQUEST)
                if timezone.is_naive(start_parsed):
                    start_parsed = timezone.make_aware(start_parsed, timezone.get_current_timezone())
                end_parsed = start_parsed + datetime.timedelta(minutes=duration_minutes)
                end_dt = end_parsed.isoformat(timespec='seconds')
            except Exception:
                return Response({'detail': 'Falha ao calcular término.'}, status=status.HTTP_400_BAD_REQUEST)

        # Use serializer to validate and create
        payload = {
            'barber': barber.id,
            'client_name': data.get('client_name') or data.get('clientName') or data.get('nome'),
            'client_phone': data.get('client_phone') or data.get('clientPhone') or data.get('telefone'),
            'service': service_id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'notes': data.get('notes') or data.get('obs')
        }
        serializer = AppointmentSerializer(data=payload)
        if serializer.is_valid():
            try:
                appt = serializer.save()
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(AppointmentSerializer(appt).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.

@method_decorator(csrf_exempt, name='dispatch')
class PublicAppointmentCancel(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        """Cancela um agendamento publicamente por ID.
        Segurança mínima: exige apenas o ID; ajuste conforme necessário.
        """
        appt_id = request.data.get('id') or request.data.get('appointmentId')
        if not appt_id:
            return Response({'detail': 'Parâmetro "id" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            appt = Appointment.objects.get(pk=appt_id)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Agendamento não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Marcar actor como None para auditoria pública e cancelar
        setattr(appt, '_actor', None)
        appt.status = Appointment.STATUS_CANCELLED
        appt.save()
        try:
            Sale.objects.filter(appointment=appt).update(status='cancelled')
        except Exception:
            pass
        return Response(AppointmentSerializer(appt).data, status=status.HTTP_200_OK)
