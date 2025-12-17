from django.shortcuts import render, redirect
import os
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
import csv
from .models import User
from django.utils import timezone
from appointments.models import Appointment, TimeBlock
import datetime
from services.models import Service
from sales.models import Sale, Withdrawal
from audit.models import AuditLog
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from audit.models import AuditLog
import datetime
from sales.models import Sale, Withdrawal
from django.db.models import Sum



@login_required
def painel_index(request: HttpRequest):
    user: User = request.user  # type: ignore
    if user.role == User.BARBER:
        return redirect('dashboard_barber')
    return redirect('dashboard_admin')


@login_required
def dashboard_barber(request: HttpRequest):
    user: User = request.user  # type: ignore
    now_local = timezone.localtime()
    # Auto-concluir agendamentos passados (comparação em UTC)
    Appointment.objects.filter(status='scheduled', end_datetime__lte=timezone.now()).update(status='done')
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    appts_today = Appointment.objects.filter(
        barber=user,
        start_datetime__gte=today_start,
        start_datetime__lt=today_end,
    ).order_by('start_datetime')

    sales_today = Sale.objects.filter(
        barber=user,
        created_at__gte=today_start,
        created_at__lt=today_end,
        status='paid'
    )

    appts_done_today = appts_today.filter(status='done')
    appts_value_today = appts_done_today.aggregate(total=Sum('service__price'))['total'] or 0
    sales_value_today = sales_today.aggregate(total=Sum('amount'))['total'] or 0
    day_revenue = (appts_value_today or 0) + (sales_value_today or 0)

    # Próximo horário: apenas agendamentos futuros do dia com status 'scheduled'
    next_appointment = Appointment.objects.filter(
        barber=user,
        status=Appointment.STATUS_SCHEDULED,
        start_datetime__gte=now_local,
        start_datetime__lt=today_end,
    ).order_by('start_datetime').first()

    kpis = {
        'appointments_count': appts_today.count(),
        'sales_count': sales_today.count(),
        'sales_total': day_revenue,
        'next_appointment': next_appointment,
    }

    return render(request, 'dashboard_barber.html', {
        'kpis': kpis,
        'appointments_today': appts_today,
    })


@login_required
def dashboard_admin(request: HttpRequest):
    now_local = timezone.localtime()
    # Auto-concluir agendamentos passados (comparação em UTC)
    Appointment.objects.filter(status='scheduled', end_datetime__lte=timezone.now()).update(status='done')
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)

    appts_today = Appointment.objects.filter(
        start_datetime__gte=today_start,
        start_datetime__lt=today_end,
    )
    sales_today = Sale.objects.filter(
        created_at__gte=today_start,
        created_at__lt=today_end,
        status='paid'
    )

    status_breakdown = appts_today.values('status').annotate(c=Count('id'))
    appts_done_today = appts_today.filter(status='done')
    appts_value_today = appts_done_today.aggregate(total=Sum('service__price'))['total'] or 0
    sales_value_today = sales_today.aggregate(total=Sum('amount'))['total'] or 0
    sales_total = (appts_value_today or 0) + (sales_value_today or 0)
    # Exibir número de barbeiros como 5
    barbers_count = 5

    return render(request, 'dashboard_admin.html', {
        'kpis': {
            'appointments_count': appts_today.count(),
            'sales_count': sales_today.count(),
            'sales_total': sales_total,
            'barbers_count': barbers_count,
        },
        'status_breakdown': status_breakdown,
        'appointments_today': appts_today.order_by('start_datetime')[:10],
    })


@login_required
def panel_appointments(request: HttpRequest):
    user: User = request.user  # type: ignore
    now_local = timezone.localtime()
    # Auto-concluir agendamentos passados (comparação em UTC)
    Appointment.objects.filter(status='scheduled', end_datetime__lte=timezone.now()).update(status='done')
    # Histórico completo, incluindo passados, mais recentes primeiro
    special_all_view = (getattr(user, 'username', '') or '').lower() in ['kaue', 'alafy', 'alafi', 'alefi']
    # Ajuste: todos os barbeiros podem ver todos os agendamentos
    # Mantemos is_admin=True para habilitar colunas de "Barbeiro" no CSV quando visualizam tudo
    if user.role in {User.ADMIN, User.BARBER} or special_all_view:
        qs = Appointment.objects.all().order_by('-start_datetime')
        is_admin = True
    else:
        qs = Appointment.objects.filter(barber=user).order_by('-start_datetime')
        is_admin = False

    # Exportação CSV
    if request.GET.get('export') == 'csv':
        rows = qs.select_related('barber', 'service').order_by('-start_datetime')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="agendamentos.csv"'
        writer = csv.writer(response)
        if is_admin:
            writer.writerow(['Data', 'Hora', 'Barbeiro', 'Cliente', 'Telefone', 'Serviço', 'Status'])
        else:
            writer.writerow(['Data', 'Hora', 'Cliente', 'Telefone', 'Serviço', 'Status'])
        for a in rows:
            date_str = timezone.localtime(a.start_datetime).strftime('%d/%m/%Y')
            time_str = timezone.localtime(a.start_datetime).strftime('%H:%M')
            base = [date_str, time_str]
            if is_admin:
                base.append(getattr(a.barber, 'display_name', None) or getattr(a.barber, 'username', ''))
            base.extend([a.client_name, a.client_phone or '', getattr(a.service, 'title', ''), a.status])
            writer.writerow(base)
        return response

    # Paginação: 20 por página (por barbeiro)
    PER_PAGE = 20
    try:
        page_number = int(request.GET.get('page', 1))
    except Exception:
        page_number = 1
    # Lista de todos os barbeiros para exibir colunas mesmo sem agendamentos
    barbers_all = list(User.objects.filter(role=User.BARBER).order_by('display_name', 'username'))
    # Reordenar para que o barbeiro logado apareça primeiro na lista
    if getattr(user, 'role', None) == User.BARBER:
        try:
            barbers_all = [b for b in barbers_all if b.id == user.id] + [b for b in barbers_all if b.id != user.id]
        except Exception:
            pass
    # Agrupar itens desta página por barbeiro e calcular páginas máximas
    max_pages = 1
    appointments_groups = []
    for b in barbers_all:
        bqs = qs.filter(barber_id=b.id)
        count_b = bqs.count()
        pages_b = ((count_b + PER_PAGE - 1) // PER_PAGE) if count_b else 1
        if pages_b > max_pages:
            max_pages = pages_b
        start = (page_number - 1) * PER_PAGE
        end = start + PER_PAGE
        blist = list(bqs[start:end])
        appointments_groups.append({'barber': b, 'list': blist})

    # Criar um paginator "dummy" apenas para a navegação de páginas no template
    dummy_items = list(range(max_pages * PER_PAGE))
    paginator = Paginator(dummy_items, PER_PAGE)
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel_appointments.html', {
        'appointments_page': page_obj,
        'paginator': paginator,
        'is_admin': is_admin,
        'appointments_groups': appointments_groups,
    })


@login_required
def panel_finances(request: HttpRequest):
    user: User = request.user  # type: ignore
    # Auto-concluir agendamentos passados (comparação em UTC)
    Appointment.objects.filter(status='scheduled', end_datetime__lte=timezone.now()).update(status='done')
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timezone.timedelta(days=1)
    month_start = today_start.replace(day=1)

    sales_filter = {}
    appts_filter = {}
    is_admin = user.role == User.ADMIN
    # Usuários especiais (Kaue/Alafy) devem enxergar o resumo por serviço do mês
    # somado de todos os barbeiros, mesmo não sendo admin.
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    if not is_admin:
        sales_filter['barber'] = user
        appts_filter['barber'] = user

    # Handle withdrawal POST (Kaue/Alafy only)
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    if request.method == 'POST' and (not is_admin) and is_special_finances_view:
        amount_str = (request.POST.get('withdraw_amount') or '').strip().replace(',', '.')
        reason = (request.POST.get('withdraw_reason') or '').strip()
        note_raw = (request.POST.get('withdraw_note') or '').strip()
        note = (f"[{reason}] {note_raw}" if reason else note_raw)
        try:
            amt = Decimal(amount_str)
            if amt <= 0:
                raise ValueError('Informe um valor positivo para retirada.')
        except Exception:
            # Ignore errors silently in view; template can show client-side validation
            amt = None
        if amt:
            w = Withdrawal.objects.create(user=user, amount=amt, note=note)
            # Audit log for withdrawal
            try:
                AuditLog.objects.create(
                    actor=user,
                    action='create',
                    target_type='Withdrawal',
                    target_id=str(w.pk),
                    payload={
                        'amount': str(amt),
                        'note': note,
                        'reason': reason,
                        'barber': getattr(user, 'id', None),
                        'barber_label': (getattr(user, 'display_name', None) or getattr(user, 'username', None)),
                    }
                )
            except Exception:
                pass

    sales_today = Sale.objects.filter(created_at__gte=today_start, created_at__lt=today_end, **sales_filter)
    sales_month = Sale.objects.filter(created_at__gte=month_start, created_at__lt=today_end, **sales_filter)
    # Concluídos hoje: usar end_datetime (momento da conclusão real)
    appts_completed_today = Appointment.objects.filter(status='done', end_datetime__gte=today_start, end_datetime__lt=today_end, **appts_filter)
    # Mês: usar end_datetime para refletir receita reconhecida na conclusão
    appts_month_done = Appointment.objects.filter(status='done', end_datetime__gte=month_start, end_datetime__lt=today_end, **appts_filter)

    # KPIs baseados em agendamentos concluídos + vendas pagas
    appts_today_value = appts_completed_today.aggregate(total=Sum('service__price'))['total'] or 0
    appts_month_value = appts_month_done.aggregate(total=Sum('service__price'))['total'] or 0
    sales_today_value = sales_today.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    sales_month_value = sales_month.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    # Cancelados hoje (considerando janela pelo start_datetime, como nos painéis)
    appts_cancelled_today = Appointment.objects.filter(
        status='cancelled',
        start_datetime__gte=today_start,
        start_datetime__lt=today_end,
        **appts_filter,
    )
    kpis = {
        'today_revenue': (appts_today_value or 0) + (sales_today_value or 0),
        'month_revenue': (appts_month_value or 0) + (sales_month_value or 0),
        'sales_count': sales_today.count(),
        # Concluídos Hoje deve incluir vendas registradas hoje
        'appts_completed': appts_completed_today.count() + sales_today.count(),
        'appts_cancelled': appts_cancelled_today.count(),
    }

    # Faturamento total do mês (todos os barbeiros) somente para Kaue/Alafy
    if (not is_admin) and is_special_finances_view:
        appts_month_all_value = Appointment.objects.filter(
            status='done',
            end_datetime__gte=month_start,
            end_datetime__lt=today_end,
        ).aggregate(total=Sum('service__price'))['total'] or 0
        sales_month_all_paid_value = Sale.objects.filter(
            created_at__gte=month_start,
            created_at__lt=today_end,
            status='paid',
        ).aggregate(total=Sum('amount'))['total'] or 0
        # Subtrair retiradas do mês para visão total
        withdrawals_month_total = Withdrawal.objects.filter(
            created_at__gte=month_start,
            created_at__lt=today_end,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        kpis['month_total_all'] = ((appts_month_all_value or 0) + (sales_month_all_paid_value or 0)) - (withdrawals_month_total or Decimal('0'))

    # Participação do barbeiro (Mês) baseada somente em serviços concluídos
    if not is_admin:
        uname = (user.username or '').lower()
        # Total de serviços concluídos do próprio barbeiro no mês (appts_month_done já aplica filtro do barbeiro)
        self_services_month = appts_month_done.aggregate(total=Sum('service__price'))['total'] or Decimal('0')
        share_month: Decimal = Decimal('0')
        if uname in ['rikelv', 'emerson', 'kevin']:
            # 60% do total dos serviços do próprio barbeiro no mês
            share_month = self_services_month * Decimal('0.60')
        elif uname in ['kaue', 'alefi', 'alafy', 'alafi']:
            # 40% dos serviços dos três barbeiros (rikelv, emerson, kevin) no mês + 100% dos próprios serviços no mês
            others_q = Q(barber__username__iexact='rikelv') | Q(barber__username__iexact='emerson') | Q(barber__username__iexact='kevin')
            others_services_month = Appointment.objects.filter(
                status='done',
                end_datetime__gte=month_start,
                end_datetime__lt=today_end,
            ).filter(others_q).aggregate(total=Sum('service__price'))['total'] or Decimal('0')
            share_month = (others_services_month * Decimal('0.40')) + (self_services_month * Decimal('1.00'))
        # Garantir duas casas decimais
        kpis['barber_share_month'] = share_month.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    recent_sales = Sale.objects.filter(**sales_filter).order_by('-created_at')[:10]

    # Breakdowns for month-to-date (done appointments)
    # Fonte para o resumo por serviço:
    # - Admin: todos os barbeiros
    # - Kaue/Alafy: todos os barbeiros
    # - Demais barbeiros: apenas seus próprios serviços
    breakdown_source_qs = (
        Appointment.objects.filter(
            status='done',
            end_datetime__gte=month_start,
            end_datetime__lt=today_end,
        ) if (is_admin or is_special_finances_view) else appts_month_done
    )

    # Quebra por serviço baseada em agendamentos concluídos
    appt_breakdown = breakdown_source_qs.values('service__id', 'service__title').annotate(
        count=Count('id'),
        total_value=Sum('service__price')
    )
    # Incluir vendas com serviço como novos serviços feitos (mês)
    sales_breakdown = Sale.objects.filter(
        created_at__gte=month_start,
        created_at__lt=today_end,
        status='paid',
        **sales_filter
    ).filter(service__isnull=False).values('service__id', 'service__title').annotate(
        count=Count('id'),
        total_value=Sum('amount')
    )
    # Merge por service__id
    combined_map = {}
    for r in appt_breakdown:
        sid = r['service__id']
        combined_map[sid] = {
            'service__id': sid,
            'service__title': r['service__title'],
            'count': r['count'],
            'total_value': r['total_value'] or 0,
        }
    for s in sales_breakdown:
        sid = s['service__id']
        entry = combined_map.get(sid, {
            'service__id': sid,
            'service__title': s['service__title'],
            'count': 0,
            'total_value': 0,
        })
        entry['count'] += s['count']
        entry['total_value'] += (s['total_value'] or 0)
        combined_map[sid] = entry
    breakdown_by_service = sorted(combined_map.values(), key=lambda x: x['total_value'], reverse=True)
    breakdown_by_barber = appts_month_done.exclude(barber__username__iexact='teste').exclude(barber__display_name__iexact='Teste Barber').values('barber__id', 'barber__display_name', 'barber__username').annotate(
        count=Count('id'),
        total_value=Sum('service__price')
    ).order_by('-total_value')

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="financas_export.csv"'
        writer = csv.writer(response)
        timeline_range = (request.GET.get('timeline_range') or '30').lower()
        timeline_compare = (request.GET.get('timeline_compare') or '0').lower() in ('1','true','on')
        include_edited = (request.GET.get('include_edited') or '0').lower() in ('1','true','on')
        services_month = request.GET.get('services_month') or ''
        services_compare = (request.GET.get('services_compare') or '0').lower() in ('1','true','on')
        services_month_compare = request.GET.get('services_month_compare') or ''
        barber_range = (request.GET.get('barber_range') or '30').lower()

        def _mk_timeline(rng):
            now_loc = timezone.localtime()
            if rng in ('day', 'today'):
                start_l = now_loc.replace(hour=0, minute=0, second=0, microsecond=0)
                end_l = start_l + timezone.timedelta(days=1)
                gran = 'hour'
            elif rng in ('week','7'):
                start_l = now_loc - timezone.timedelta(days=7)
                end_l = now_loc
                gran = 'day'
            elif rng in ('15',):
                start_l = now_loc - timezone.timedelta(days=15)
                end_l = now_loc
                gran = 'day'
            else:
                start_l = now_loc - timezone.timedelta(days=30)
                end_l = now_loc
                gran = 'day'
            apf = {}
            if not (is_admin or is_special_finances_view):
                apf['barber'] = user
            cur = start_l
            pts = []
            det = {}
            if gran == 'hour':
                step = timezone.timedelta(hours=1)
            else:
                step = timezone.timedelta(days=1)
            while cur < end_l:
                nxt = cur + step
                ub = cur.astimezone(datetime.timezone.utc)
                ue = nxt.astimezone(datetime.timezone.utc)
                done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=ub, start_datetime__lt=ue, **apf)
                ids = set(done_qs.values_list('id', flat=True))
                if include_edited:
                    edits = AuditLog.objects.filter(action='update', target_type='Appointment', timestamp__gte=ub, timestamp__lt=ue)
                    eids = set()
                    for t in edits.values_list('target_id', flat=True):
                        try:
                            eids.add(int(t))
                        except Exception:
                            pass
                    ids |= eids
                ts = int(cur.astimezone(datetime.timezone.utc).timestamp()*1000)
                services = list({getattr(a.service, 'title', '') for a in done_qs})
                det[ts] = services
                pts.append([ts, len(ids)])
                cur = nxt
            return pts, det

        writer.writerow(['Agendamentos concluídos'])
        writer.writerow(['Período', timeline_range])
        pts, det = _mk_timeline(timeline_range)
        writer.writerow(['Timestamp(ms)', 'Concluídos', 'Serviços'])
        for ts,val in pts:
            writer.writerow([ts, val, '; '.join(det.get(ts, []))])
        if timeline_compare:
            now_loc = timezone.localtime()
            if timeline_range in ('day','today'):
                prev_start = now_loc.replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=1)
                prev_end = prev_start + timezone.timedelta(days=1)
            elif timeline_range in ('week','7'):
                prev_start = now_loc - timezone.timedelta(days=14)
                prev_end = now_loc - timezone.timedelta(days=7)
            elif timeline_range in ('15',):
                prev_start = now_loc - timezone.timedelta(days=30)
                prev_end = now_loc - timezone.timedelta(days=15)
            else:
                prev_start = now_loc - timezone.timedelta(days=60)
                prev_end = now_loc - timezone.timedelta(days=30)
            rng_prev = 'compare'
            writer.writerow([])
            writer.writerow(['Agendamentos concluídos (comparação)'])
            writer.writerow(['Período', rng_prev])
            # shift logic by passing explicit interval
            def _mk_interval(s_l, e_l, gran):
                apf = {}
                if not (is_admin or is_special_finances_view):
                    apf['barber'] = user
                cur = s_l
                pts = []
                det = {}
                step = timezone.timedelta(hours=1) if gran=='hour' else timezone.timedelta(days=1)
                while cur < e_l:
                    nxt = cur + step
                    ub = cur.astimezone(datetime.timezone.utc)
                    ue = nxt.astimezone(datetime.timezone.utc)
                    done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=ub, start_datetime__lt=ue, **apf)
                    ids = set(done_qs.values_list('id', flat=True))
                    if include_edited:
                        edits = AuditLog.objects.filter(action='update', target_type='Appointment', timestamp__gte=ub, timestamp__lt=ue)
                        eids = set()
                        for t in edits.values_list('target_id', flat=True):
                            try:
                                eids.add(int(t))
                            except Exception:
                                pass
                        ids |= eids
                    ts = int(cur.astimezone(datetime.timezone.utc).timestamp()*1000)
                    services = list({getattr(a.service, 'title', '') for a in done_qs})
                    det[ts] = services
                    pts.append([ts, len(ids)])
                    cur = nxt
                return pts, det
            gran = 'hour' if timeline_range in ('day','today') else 'day'
            pts2, det2 = _mk_interval(prev_start, prev_end, gran)
            writer.writerow(['Timestamp(ms)', 'Concluídos', 'Serviços'])
            for ts,val in pts2:
                writer.writerow([ts, val, '; '.join(det2.get(ts, []))])

        writer.writerow([])
        writer.writerow(['Serviços mais agendados'])
        month_sel = services_month
        now_local2 = timezone.localtime()
        try:
            parts = (month_sel or '').split('-')
            year = int(parts[0]) if len(parts)>=1 and parts[0] else now_local2.year
            month = int(parts[1]) if len(parts)>=2 and parts[1] else now_local2.month
            start_l = datetime.datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=now_local2.tzinfo)
        except Exception:
            start_l = now_local2.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_l = start_l.replace(month=start_l.month + 1) if start_l.month < 12 else start_l.replace(year=start_l.year+1, month=1)
        apf2 = {}
        if not (is_admin or is_special_finances_view):
            apf2['barber'] = user
        ub = start_l.astimezone(datetime.timezone.utc)
        ue = end_l.astimezone(datetime.timezone.utc)
        rows = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=ub, end_datetime__lt=ue, **apf2).values('service__title').annotate(c=Count('id')).order_by('-c')
        writer.writerow(['Serviço', 'Concluídos'])
        for r in rows:
            writer.writerow([r['service__title'] or 'Serviço', int(r['c'] or 0)])
        if services_compare and services_month_compare:
            writer.writerow([])
            writer.writerow(['Serviços mais agendados (comparação)'])
            parts = (services_month_compare or '').split('-')
            try:
                year = int(parts[0]) if len(parts)>=1 and parts[0] else now_local2.year
                month = int(parts[1]) if len(parts)>=2 and parts[1] else now_local2.month
                start_l2 = datetime.datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=now_local2.tzinfo)
            except Exception:
                start_l2 = now_local2.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_l2 = start_l2.replace(month=start_l2.month + 1) if start_l2.month < 12 else start_l2.replace(year=start_l2.year+1, month=1)
            ub2 = start_l2.astimezone(datetime.timezone.utc)
            ue2 = end_l2.astimezone(datetime.timezone.utc)
            rows2 = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=ub2, end_datetime__lt=ue2, **apf2).values('service__title').annotate(c=Count('id')).order_by('-c')
            writer.writerow(['Serviço', 'Concluídos'])
            for r in rows2:
                writer.writerow([r['service__title'] or 'Serviço', int(r['c'] or 0)])

        writer.writerow([])
        writer.writerow(['Quantidade de serviços por barbeiro'])
        rng = barber_range
        now_local3 = timezone.localtime()
        if rng in ('today','day'):
            start_l = now_local3.replace(hour=0, minute=0, second=0, microsecond=0)
            end_l = now_local3
        elif rng in ('7','week'):
            start_l = now_local3 - timezone.timedelta(days=7)
            end_l = now_local3
        elif rng in ('15',):
            start_l = now_local3 - timezone.timedelta(days=15)
            end_l = now_local3
        elif rng in ('60','2m','2mes','2meses'):
            start_l = now_local3 - timezone.timedelta(days=60)
            end_l = now_local3
        else:
            start_l = now_local3 - timezone.timedelta(days=30)
            end_l = now_local3
        ub3 = start_l.astimezone(datetime.timezone.utc)
        ue3 = end_l.astimezone(datetime.timezone.utc)
        qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=ub3, end_datetime__lt=ue3)
        rows3 = list(qs.values('barber').annotate(c=Count('id')).order_by('-c'))
        counts_map = {r['barber']: int(r.get('c') or 0) for r in rows3}
        all_barbers = list(User.objects.filter(role=User.BARBER).order_by('display_name', 'username'))
        def _norm(s):
            return (s or '').strip().lower()
        all_barbers = [u for u in all_barbers if _norm(getattr(u, 'display_name', '')) not in {'teste barber','test barber'} and _norm(getattr(u, 'username', '')) not in {'teste','test'}]
        all_barbers.sort(key=lambda u: counts_map.get(u.id, 0), reverse=True)
        writer.writerow(['Barbeiro', 'Concluídos'])
        for u in all_barbers:
            writer.writerow([getattr(u, 'display_name', None) or getattr(u, 'username', ''), counts_map.get(u.id, 0)])

        if is_special_finances_view and not is_admin:
            writer.writerow([])
            writer.writerow(['Retiradas por motivo (últimos 30 dias)'])
            now4 = timezone.localtime()
            start4 = now4 - timezone.timedelta(days=30)
            end4 = now4
            ub4 = start4.astimezone(datetime.timezone.utc)
            ue4 = end4.astimezone(datetime.timezone.utc)
            cats = ['Fornecedores', 'Itens básicos', 'Aluguel Agua/Luz', 'Produtos Freezer', 'Outros']
            sums = {c: Decimal('0') for c in cats}
            for w in Withdrawal.objects.filter(created_at__gte=ub4, created_at__lt=ue4):
                note = (getattr(w, 'note', '') or '')
                reason = 'Outros'
                if note.startswith('['):
                    try:
                        end_idx = note.find(']')
                        if end_idx > 1:
                            tag = note[1:end_idx].strip()
                            reason = tag if tag in sums else 'Outros'
                    except Exception:
                        reason = 'Outros'
                amt = getattr(w, 'amount', Decimal('0')) or Decimal('0')
                sums[reason] = (sums.get(reason, Decimal('0')) + amt)
            ordered = sorted(((c, sums[c]) for c in cats), key=lambda x: x[1], reverse=True)
            writer.writerow(['Motivo', 'Valor (R$)'])
            for c,v in ordered:
                writer.writerow([c, str(v)])

        return response

    return render(request, 'panel_finances.html', {
        'kpis': kpis,
        'recent_sales': recent_sales,
        'completed_today': appts_completed_today.order_by('end_datetime'),
        'is_admin': is_admin,
        'is_special_finances_view': is_special_finances_view,
        'can_withdraw': (not is_admin) and is_special_finances_view,
        'breakdown_by_service': breakdown_by_service,
        'breakdown_by_barber': breakdown_by_barber,
        'all_services': Service.objects.filter(active=True).order_by('title'),
    })


@login_required
def finances_chart_data(request: HttpRequest):
    """Return JSON timeseries for finances chart.
    Query params:
      - range: 'day'|'week'|'15'|'30' (default '30')
      - compare: '1' to include previous-period comparison
      - include_edited: '1' to include appointments that had updates (AuditLog)
    """
    rng = request.GET.get('range', '30')
    compare = request.GET.get('compare', '0') in ('1', 'true', 'on')
    include_edited = request.GET.get('include_edited', '0') in ('1', 'true', 'on')
    now_local = timezone.localtime()

    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    appts_filter = {}
    if not (is_admin or is_special_finances_view):
        appts_filter['barber'] = user

    def mk_range_points(start_local, end_local, granularity='day'):
        points = []
        details = {}
        cur = start_local
        if granularity == 'hour':
            step = datetime.timedelta(hours=1)
            while cur < end_local:
                nxt = cur + step
                utc_beg = cur.astimezone(datetime.timezone.utc)
                utc_end = nxt.astimezone(datetime.timezone.utc)
                # count done appointments
                done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=utc_beg, start_datetime__lt=utc_end, **appts_filter)
                done_ids = set(done_qs.values_list('id', flat=True))
                count_ids = set(done_ids)
                if include_edited:
                    edits = AuditLog.objects.filter(action='update', target_type='Appointment', timestamp__gte=utc_beg, timestamp__lt=utc_end)
                    edit_ids = set()
                    for t in edits.values_list('target_id', flat=True):
                        try:
                            edit_ids.add(int(t))
                        except Exception:
                            pass
                    count_ids |= edit_ids
                ts = int(cur.astimezone(datetime.timezone.utc).timestamp() * 1000)
                # prepare list of service titles for this bucket
                services = list({getattr(a.service, 'title', '') for a in done_qs})
                details[ts] = services
                points.append([ts, len(count_ids)])
                cur = nxt
            return points, details
        else:
            # daily granularity
            step = datetime.timedelta(days=1)
            while cur < end_local:
                nxt = (cur + step)
                utc_beg = cur.astimezone(datetime.timezone.utc)
                utc_end = nxt.astimezone(datetime.timezone.utc)
                done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=utc_beg, start_datetime__lt=utc_end, **appts_filter)
                done_ids = set(done_qs.values_list('id', flat=True))
                count_ids = set(done_ids)
                if include_edited:
                    edits = AuditLog.objects.filter(action='update', target_type='Appointment', timestamp__gte=utc_beg, timestamp__lt=utc_end)
                    edit_ids = set()
                    for t in edits.values_list('target_id', flat=True):
                        try:
                            edit_ids.add(int(t))
                        except Exception:
                            pass
                    count_ids |= edit_ids
                ts = int(cur.astimezone(datetime.timezone.utc).timestamp() * 1000)
                services = list({getattr(a.service, 'title', '') for a in done_qs})
                details[ts] = services
                points.append([ts, len(count_ids)])
                cur = nxt
            return points, details

    # determine start/end/local and granularity
    if rng == 'day':
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + datetime.timedelta(days=1)
        gran = 'hour'
        period_len = datetime.timedelta(days=1)
    elif rng == 'week':
        end_local = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_local = end_local - datetime.timedelta(days=6)
        start_local = start_local.replace(hour=0, minute=0, second=0, microsecond=0)
        gran = 'day'
        period_len = datetime.timedelta(days=7)
    elif rng == '15':
        end_local = now_local
        start_local = (now_local - datetime.timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
        gran = 'day'
        period_len = datetime.timedelta(days=15)
    else:
        # default 30
        end_local = now_local
        start_local = (now_local - datetime.timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        gran = 'day'
        period_len = datetime.timedelta(days=30)

    series_main, details_main = mk_range_points(start_local, end_local, gran)

    out_series = [
        {
            'name': 'Período atual',
            'data': series_main,
        }
    ]
    out_details = {'current': details_main}

    if compare:
        prev_start = start_local - period_len
        prev_end = start_local
        series_prev, details_prev = mk_range_points(prev_start, prev_end, gran)
        out_series.append({
            'name': 'Comparação (período anterior)',
            'data': series_prev,
        })
        out_details['compare'] = details_prev

    return JsonResponse({'series': out_series, 'details': out_details})


@login_required
def finances_revenue_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    month_str = request.GET.get('month') or ''
    now_local = timezone.localtime()
    try:
        parts = (month_str or '').split('-')
        year = int(parts[0]) if len(parts) >= 1 and parts[0] else now_local.year
        month = int(parts[1]) if len(parts) >= 2 and parts[1] else now_local.month
        start_local = datetime.datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=now_local.tzinfo)
    except Exception:
        start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_local.month == 12:
        end_local = start_local.replace(year=start_local.year + 1, month=1)
    else:
        end_local = start_local.replace(month=start_local.month + 1)

    sales_filter = {}
    appts_filter = {}
    withdraw_filter = {}
    if not (is_admin or is_special_finances_view):
        sales_filter['barber'] = user
        appts_filter['barber'] = user
        withdraw_filter['user'] = user

    step = datetime.timedelta(days=1)
    points = []
    cur = start_local
    while cur < end_local:
        nxt = cur + step
        utc_beg = cur.astimezone(datetime.timezone.utc)
        utc_end = nxt.astimezone(datetime.timezone.utc)
        appts_val = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=utc_beg, end_datetime__lt=utc_end, **appts_filter).aggregate(total=Sum('service__price'))['total'] or 0
        sales_val = Sale.objects.filter(created_at__gte=utc_beg, created_at__lt=utc_end, status='paid', **sales_filter).aggregate(total=Sum('amount'))['total'] or 0
        withdraw_val = Withdrawal.objects.filter(created_at__gte=utc_beg, created_at__lt=utc_end, **withdraw_filter).aggregate(total=Sum('amount'))['total'] or 0
        net = (appts_val or 0) + (sales_val or 0) - (withdraw_val or 0)
        ts = int(cur.astimezone(datetime.timezone.utc).timestamp() * 1000)
        points.append([ts, float(net)])
        cur = nxt

    series = [{ 'name': 'Receita líquida', 'data': points }]
    return JsonResponse({'series': series})


@login_required
def finances_services_breakdown_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    month_str = request.GET.get('month') or ''
    now_local = timezone.localtime()
    try:
        parts = (month_str or '').split('-')
        year = int(parts[0]) if len(parts) >= 1 and parts[0] else now_local.year
        month = int(parts[1]) if len(parts) >= 2 and parts[1] else now_local.month
        start_local = datetime.datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=now_local.tzinfo)
    except Exception:
        start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_local.month == 12:
        end_local = start_local.replace(year=start_local.year + 1, month=1)
    else:
        end_local = start_local.replace(month=start_local.month + 1)

    appts_filter = {}
    if not (is_admin or is_special_finances_view):
        appts_filter['barber'] = user

    utc_beg = start_local.astimezone(datetime.timezone.utc)
    utc_end = end_local.astimezone(datetime.timezone.utc)

    qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=utc_beg, end_datetime__lt=utc_end, **appts_filter)
    rows = qs.values('service__title').annotate(c=Count('id')).order_by('-c')
    labels = []
    series = []
    for r in rows:
        title = r['service__title'] or 'Serviço'
        labels.append(title)
        series.append(int(r['c'] or 0))

    if not labels:
        labels = ['Sem registros']
        series = [0]

    return JsonResponse({'labels': labels, 'series': series})

@login_required
def finances_withdrawals_funnel_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    if not is_special_finances_view or is_admin:
        return JsonResponse({'labels': [], 'series': []})
    now_local = timezone.localtime()
    start_local = now_local - timezone.timedelta(days=30)
    end_local = now_local
    utc_beg = start_local.astimezone(datetime.timezone.utc)
    utc_end = end_local.astimezone(datetime.timezone.utc)
    qs = Withdrawal.objects.filter(created_at__gte=utc_beg, created_at__lt=utc_end)
    cats = ['Fornecedores', 'Itens básicos', 'Aluguel Agua/Luz', 'Produtos Freezer', 'Outros']
    sums = {c: Decimal('0') for c in cats}
    for w in qs:
        note = (getattr(w, 'note', '') or '')
        reason = 'Outros'
        if note.startswith('['):
            try:
                end_idx = note.find(']')
                if end_idx > 1:
                    tag = note[1:end_idx].strip()
                    reason = tag if tag in sums else 'Outros'
            except Exception:
                reason = 'Outros'
        amt = getattr(w, 'amount', Decimal('0')) or Decimal('0')
        sums[reason] = (sums.get(reason, Decimal('0')) + amt)
    ordered = sorted(((c, sums[c]) for c in cats), key=lambda x: x[1], reverse=True)
    labels = [c for c, _ in ordered]
    series = [float(v) for _, v in ordered]
    return JsonResponse({'labels': labels, 'series': series})

@login_required
def finances_no_show_rate_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    # Visão padrão: últimos 30 dias
    now_local = timezone.localtime()
    start_local = now_local - timezone.timedelta(days=30)
    end_local = now_local
    step = timezone.timedelta(days=1)

    labels = []
    done_rates = []
    cancel_rates = []

    cur = start_local
    while cur < end_local:
        nxt = cur + step
        utc_beg = cur.astimezone(datetime.timezone.utc)
        utc_end = nxt.astimezone(datetime.timezone.utc)
        # concluir por fim do serviço no dia
        done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, end_datetime__gte=utc_beg, end_datetime__lt=utc_end)
        # cancelados considerados pelo início dentro do dia
        cancel_qs = Appointment.objects.filter(status=Appointment.STATUS_CANCELLED, start_datetime__gte=utc_beg, start_datetime__lt=utc_end)
        total = done_qs.count() + cancel_qs.count()
        dr = float((done_qs.count() / total) * 100) if total else 0.0
        cr = float((cancel_qs.count() / total) * 100) if total else 0.0
        labels.append(timezone.localtime(cur).strftime('%d/%m'))
        done_rates.append(round(dr, 2))
        cancel_rates.append(round(cr, 2))
        cur = nxt

    return JsonResponse({
        'labels': labels,
        'series': {
            'done_rate': done_rates,
            'cancel_rate': cancel_rates,
        }
    })

@login_required
def finances_barber_stats_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    rng = (request.GET.get('range') or '').strip().lower()
    now_local = timezone.localtime()
    month_param = (request.GET.get('month') or '').strip()
    if month_param:
        try:
            parts = month_param.split('-')
            year = int(parts[0]) if len(parts) >= 1 and parts[0] else now_local.year
            month = int(parts[1]) if len(parts) >= 2 and parts[1] else now_local.month
            start_local = datetime.datetime(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=now_local.tzinfo)
        except Exception:
            start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_local.month == 12:
            end_local = start_local.replace(year=start_local.year + 1, month=1)
        else:
            end_local = start_local.replace(month=start_local.month + 1)
    elif rng in ('today', 'day'):
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local
    elif rng in ('7', 'week'):
        start_local = now_local - timezone.timedelta(days=7)
        end_local = now_local
    elif rng in ('15',):
        start_local = now_local - timezone.timedelta(days=15)
        end_local = now_local
    elif rng in ('60', '2m', '2meses', '2mes'):
        start_local = now_local - timezone.timedelta(days=60)
        end_local = now_local
    else:
        start_local = now_local - timezone.timedelta(days=30)
        end_local = now_local

    utc_beg = start_local.astimezone(datetime.timezone.utc)
    utc_end = end_local.astimezone(datetime.timezone.utc)

    qs = Appointment.objects.filter(
        status=Appointment.STATUS_DONE,
        end_datetime__gte=utc_beg,
        end_datetime__lt=utc_end,
    )

    rows = list(qs.values('barber').annotate(c=Count('id')).order_by('-c'))
    counts_map = {r['barber']: int(r.get('c') or 0) for r in rows}
    all_barbers = list(User.objects.filter(role=User.BARBER).order_by('display_name', 'username'))
    excluded_labels = {'teste barber', 'test barber'}
    excluded_users = {'teste', 'test'}
    def _norm(s):
        return (s or '').strip().lower()
    all_barbers = [u for u in all_barbers if _norm(getattr(u, 'display_name', '')) not in excluded_labels and _norm(getattr(u, 'username', '')) not in excluded_users]
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'assets', 'img'))
    name_to_file = {}
    try:
        for f in os.listdir(assets_dir):
            base, ext = os.path.splitext(f)
            name_to_file[base.lower()] = f
    except Exception:
        name_to_file = {}
    # Ordenar por contagem desc para gráfico mais informativo
    all_barbers.sort(key=lambda u: counts_map.get(u.id, 0), reverse=True)

    labels = []
    series = []
    barbers = []
    for u in all_barbers:
        name = (getattr(u, 'display_name', None) or getattr(u, 'username', 'Barbeiro'))
        c = counts_map.get(u.id, 0)
        avatar_url = ''
        try:
            if getattr(u, 'avatar', None):
                avatar_url = u.avatar.url
        except Exception:
            avatar_url = ''
        mapping = {
            'alafy': '/static/assets/img/alafy.JPEG',
            'emerson': '/static/assets/img/emerson.JPG',
            'kaue': '/static/assets/img/kaue.jpg',
            'kevin': '/static/assets/img/kevin.JPEG',
            'rikelv': '/static/assets/img/rikelv.JPEG',
        }
        dn = (name or '').strip().lower()
        un = (getattr(u, 'username', '') or '').strip().lower()
        if not avatar_url:
            avatar_url = mapping.get(dn) or mapping.get(un) or ''
        if not avatar_url:
            for base in [dn, un]:
                fn = name_to_file.get(base)
                if fn:
                    avatar_url = f"/static/assets/img/{fn}"
                    break
    
        labels.append(name)
        series.append(c)
        barbers.append({'id': u.id, 'name': name, 'avatar_url': avatar_url, 'count': c})

    return JsonResponse({'labels': labels, 'series': series, 'barbers': barbers})

@login_required
def finances_clients_top_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    qs = Appointment.objects.all().order_by('start_datetime')
    if not (is_admin or is_special_finances_view):
        qs = qs.filter(barber=user)
    clients = {}
    for a in qs:
        phone = ''.join(ch for ch in (a.client_phone or '') if ch.isdigit())
        if not phone:
            continue
        entry = clients.get(phone) or { 'name': a.client_name or '', 'count_done': 0 }
        if not entry['name']:
            entry['name'] = a.client_name or entry['name']
        if a.status == Appointment.STATUS_DONE:
            entry['count_done'] = int(entry['count_done']) + 1
        clients[phone] = entry
    items = [ (v['name'] or 'Cliente', int(v['count_done'] or 0)) for v in clients.values() if (int(v.get('count_done', 0)) > 0) ]
    items.sort(key=lambda x: x[1], reverse=True)
    top = items[:20]
    return JsonResponse({ 'data': top })

@login_required
def finances_occupancy_buckets_data(request: HttpRequest):
    user: User = request.user  # type: ignore
    is_admin = user.role == User.ADMIN
    special_full_access_usernames = {"kaue", "alafy", "alafi", "alefi"}
    is_special_finances_view = str(getattr(user, 'username', '')).lower() in special_full_access_usernames
    now_local = timezone.localtime()
    start_local = now_local - timezone.timedelta(days=30)
    utc_beg = start_local.astimezone(datetime.timezone.utc)
    utc_end = now_local.astimezone(datetime.timezone.utc)
    appts_filter = { 'status': Appointment.STATUS_DONE, 'start_datetime__gte': utc_beg, 'start_datetime__lt': utc_end }
    if not (is_admin or is_special_finances_view):
        appts_filter['barber'] = user
    appts_filter['service__title__icontains'] = 'corte'
    qs = Appointment.objects.filter(**appts_filter).select_related('service')
    buckets = [(8,10),(10,12),(12,14),(14,16),(16,18),(18,20)]
    counts = { f"{str(a).zfill(2)}–{str(b).zfill(2)}": 0 for a,b in buckets }
    for a in qs:
        h = timezone.localtime(a.start_datetime).hour
        for beg,end in buckets:
            if h >= beg and h < end:
                label = f"{str(beg).zfill(2)}–{str(end).zfill(2)}"
                counts[label] = counts.get(label, 0) + 1
                break
    data = [{ 'name': label, 'y': counts[label] } for label in counts.keys()]
    return JsonResponse({ 'data': data })

@login_required
def panel_clients(request: HttpRequest):
    qs = Appointment.objects.all().order_by('start_datetime')
    clients = {}
    for a in qs:
        phone = ''.join(ch for ch in (a.client_phone or '') if ch.isdigit())
        if not phone:
            continue
        entry = clients.get(phone) or {
            'phone': phone,
            'name': a.client_name or '',
            'visits': [],
            'done': [],
            'cancel': [],
            'total_spent': Decimal('0'),
        }
        entry['name'] = a.client_name or entry['name']
        entry['visits'].append(a)
        if a.status == Appointment.STATUS_DONE:
            entry['done'].append(a)
            price = getattr(getattr(a, 'service', None), 'price', Decimal('0')) or Decimal('0')
            entry['total_spent'] = (entry['total_spent'] + Decimal(str(price)))
        if a.status == Appointment.STATUS_CANCELLED:
            entry['cancel'].append(a)
        clients[phone] = entry

    data = []
    for phone, entry in clients.items():
        done_sorted = sorted(entry['done'], key=lambda x: x.end_datetime or x.start_datetime)
        last_visit = done_sorted[-1].end_datetime if done_sorted else None
        first_visit = done_sorted[0].end_datetime if done_sorted else None
        count_done = len(done_sorted)
        freq_label = ''
        if count_done >= 3 and first_visit and last_visit:
            span_days = max(1, int((last_visit - first_visit).total_seconds() // 86400))
            months = span_days / 30.0
            if months >= 1:
                rate = count_done / months
                freq_label = f"≈ {rate:.1f}x/mês"
            else:
                weeks = span_days / 7.0
                rate = count_done / max(1e-6, weeks)
                freq_label = f"≈ {rate:.1f}x/semana"
        data.append({
            'name': entry['name'],
            'phone': phone,
            'last_visit': last_visit,
            'total_spent': entry['total_spent'],
            'count_done': count_done,
            'freq_label': freq_label,
        })

    export = (request.GET.get('export') or '').strip()
    if export:
        response = HttpResponse(content_type='text/csv')
        if export == 'all':
            response['Content-Disposition'] = 'attachment; filename="clientes_all.csv"'
            writer = csv.writer(response)
            writer.writerow(['Nome', 'Telefone', 'UltimaVisita', 'TotalGasto', 'VisitasConcluidas', 'Frequencia'])
            for c in data:
                lv = timezone.localtime(c['last_visit']).strftime('%Y-%m-%d %H:%M') if c['last_visit'] else ''
                writer.writerow([c['name'], c['phone'], lv, str(c['total_spent']), c['count_done'], c['freq_label']])
            return response
        if export == 'name_phone':
            response['Content-Disposition'] = 'attachment; filename="clientes_nome_telefone.csv"'
            writer = csv.writer(response)
            writer.writerow(['Nome', 'Telefone'])
            for c in data:
                writer.writerow([c['name'], c['phone']])
            return response
        if export == 'phone':
            response['Content-Disposition'] = 'attachment; filename="clientes_telefone.csv"'
            writer = csv.writer(response)
            writer.writerow(['Telefone'])
            for c in data:
                writer.writerow([c['phone']])
            return response

    sort = (request.GET.get('sort') or '').strip()
    if sort == 'a_z':
        data.sort(key=lambda c: (c['name'] or '').casefold())
    elif sort == 'most_visits':
        data.sort(key=lambda c: c['count_done'], reverse=True)
    elif sort == 'last_appointment':
        data.sort(key=lambda c: (c['last_visit'] is not None, c['last_visit']))
    elif sort == 'total_spent':
        data.sort(key=lambda c: c['total_spent'], reverse=True)
    else:
        data.sort(key=lambda c: (c['last_visit'] is None, c['last_visit']), reverse=True)
    return render(request, 'panel_clients.html', { 'clients': data, 'sort': sort })

@login_required
def panel_profile(request: HttpRequest):
    # Permitir que barbeiros criem bloqueios de horários para o dia atual
    user: User = request.user  # type: ignore
    message = None
    message_type = 'success'

    # Usuários especiais podem bloquear horários de todos os barbeiros
    username_lower = (getattr(user, 'username', '') or '').lower()
    display_lower = (getattr(user, 'display_name', '') or '').lower()
    can_block_all = username_lower in {'kaue', 'alafy'} or display_lower in {'kaue', 'alafy'}

    # Selecionar barbeiro alvo (padrão: o próprio usuário)
    selected_barber_id_param = request.POST.get('barber_id') or request.GET.get('barberId')
    target_barber: User = user
    if can_block_all and selected_barber_id_param:
        try:
            candidate = User.objects.get(pk=int(selected_barber_id_param), role=User.BARBER)
            target_barber = candidate
        except Exception:
            target_barber = user

    if request.method == 'POST' and (request.POST.get('action') == 'upload_avatar'):
        try:
            f = request.FILES.get('avatar')
            if not f:
                raise ValueError('Selecione uma imagem válida.')
            target_barber.avatar = f
            target_barber.save()
            message = 'Foto atualizada com sucesso.'
            message_type = 'success'
        except Exception as e:
            message = str(e) if str(e) else 'Falha ao atualizar a foto.'
            message_type = 'danger'

    # Seleção de data: padrão hoje, permite até 30 dias à frente
    today = timezone.localdate()
    max_date = today + timezone.timedelta(days=30)
    selected_date_str = request.POST.get('date') or request.GET.get('date')
    try:
        selected_date = datetime.date.fromisoformat(selected_date_str) if selected_date_str else today
    except Exception:
        selected_date = today

    # Clamp ao intervalo permitido
    if selected_date < today or selected_date > max_date:
        selected_date = today
        message = 'Data fora do intervalo permitido; ajustada para hoje.'
        message_type = 'danger'

    if request.method == 'POST' and user.role == User.BARBER:
        try:
            action = (request.POST.get('action') or '').strip()
            if action == 'unblock_one':
                blk_id = request.POST.get('block_id')
                if not blk_id:
                    raise ValueError('Bloco inválido para desbloqueio.')
                # Remover bloqueio do barbeiro alvo na data selecionada
                deleted, _ = TimeBlock.objects.filter(id=blk_id, barber=target_barber, date=selected_date).delete()
                if deleted:
                    message = 'Bloqueio removido com sucesso.'
                    try:
                        AuditLog.objects.create(
                            actor=user,
                            action='delete',
                            target_type='TimeBlock',
                            target_id=str(blk_id),
                            payload={
                                'date': selected_date.isoformat(),
                                'date_display': selected_date.strftime('%d/%m'),
                                'type': 'unblock_one',
                                'barber': getattr(target_barber, 'id', None),
                                'barber_label': (getattr(target_barber, 'display_name', None) or getattr(target_barber, 'username', None)),
                            }
                        )
                    except Exception:
                        pass
                else:
                    raise ValueError('Bloqueio não encontrado.')
            elif action == 'unblock_day':
                deleted, _ = TimeBlock.objects.filter(barber=target_barber, date=selected_date).delete()
                if deleted:
                    message = 'Dia desbloqueado com sucesso.'
                    try:
                        AuditLog.objects.create(
                            actor=user,
                            action='delete',
                            target_type='TimeBlock',
                            target_id='ALL',
                            payload={
                                'date': selected_date.isoformat(),
                                'date_display': selected_date.strftime('%d/%m'),
                                'type': 'unblock_day',
                                'deleted_count': deleted,
                                'barber': getattr(target_barber, 'id', None),
                                'barber_label': (getattr(target_barber, 'display_name', None) or getattr(target_barber, 'username', None)),
                            }
                        )
                    except Exception:
                        pass
                else:
                    message = 'Nenhum bloqueio para remover nesta data.'
            else:
                full_day = bool(request.POST.get('full_day'))
                reason = (request.POST.get('reason') or '').strip()
                if full_day:
                    blk = TimeBlock.objects.create(barber=target_barber, date=selected_date, full_day=True, reason=reason)
                    message = 'Dia inteiro bloqueado com sucesso.'
                    try:
                        AuditLog.objects.create(
                            actor=user,
                            action='create',
                            target_type='TimeBlock',
                            target_id=str(blk.pk),
                            payload={
                                'date': selected_date.isoformat(),
                                'date_display': selected_date.strftime('%d/%m'),
                                'full_day': True,
                                'reason': reason,
                                'barber': getattr(target_barber, 'id', None),
                                'barber_label': (getattr(target_barber, 'display_name', None) or getattr(target_barber, 'username', None)),
                            }
                        )
                    except Exception:
                        pass
                else:
                    start_str = request.POST.get('start_time')
                    end_str = request.POST.get('end_time')
                    if not start_str or not end_str:
                        raise ValueError('Informe início e fim do intervalo.')
                    try:
                        start_parts = [int(p) for p in start_str.split(':')]
                        end_parts = [int(p) for p in end_str.split(':')]
                        start_time = timezone.datetime.now().replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0).time()
                        end_time = timezone.datetime.now().replace(hour=end_parts[0], minute=end_parts[1], second=0, microsecond=0).time()
                    except Exception:
                        raise ValueError('Horários inválidos.')
                    blk = TimeBlock(barber=target_barber, date=selected_date, start_time=start_time, end_time=end_time, full_day=False, reason=reason)
                    blk.clean()
                    blk.save()
                    message = 'Intervalo bloqueado com sucesso.'
                    try:
                        AuditLog.objects.create(
                            actor=user,
                            action='create',
                            target_type='TimeBlock',
                            target_id=str(blk.pk),
                            payload={
                                'date': selected_date.isoformat(),
                                'date_display': selected_date.strftime('%d/%m'),
                                'full_day': False,
                                'start_time': start_time.isoformat(),
                                'end_time': end_time.isoformat(),
                                'start_label': start_time.strftime('%H:%M'),
                                'end_label': end_time.strftime('%H:%M'),
                                'reason': reason,
                                'barber': getattr(target_barber, 'id', None),
                                'barber_label': (getattr(target_barber, 'display_name', None) or getattr(target_barber, 'username', None)),
                            }
                        )
                    except Exception:
                        pass
        except Exception as e:
            message_type = 'danger'
            message = str(e)

    blocks_day = TimeBlock.objects.filter(barber=target_barber, date=selected_date).order_by('full_day', 'start_time')
    # Lista de barbeiros para seleção no template (apenas para especiais)
    barbers_list = []
    if can_block_all:
        barbers_list = list(User.objects.filter(role=User.BARBER).order_by('display_name', 'username'))
    return render(request, 'panel_profile.html', {
        'message': message,
        'message_type': message_type,
        'blocks_today': blocks_day,
        'selected_date': selected_date,
        'min_date': today.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'can_block_all': can_block_all,
        'barbers': barbers_list,
        'selected_barber_id': getattr(target_barber, 'id', None),
        'selected_barber_label': (getattr(target_barber, 'display_name', None) or getattr(target_barber, 'username', None)),
    })

# Create your views here.

@login_required
def panel_history(request: HttpRequest):
    user: User = request.user  # type: ignore
    special_view = (getattr(user, 'username', '') or '').lower() in {'kaue', 'alafy'}
    if not special_view:
        return redirect('painel_index')

    # Mostrar retiradas, bloqueios, edições de agendamentos e vendas registradas
    from django.db.models import Q
    logs_qs = AuditLog.objects.filter(
        Q(target_type__in=['Withdrawal', 'TimeBlock', 'Sale']) |
        Q(target_type='Appointment', action='update')
    ).select_related('actor').order_by('-timestamp')

    # Paginação dos logs, semelhante aos agendamentos
    page_number = request.GET.get('page', 1)
    paginator = Paginator(logs_qs, 15)
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel_history.html', {
        'logs_page': page_obj,
        'paginator': paginator,
    })
