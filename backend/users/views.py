from django.shortcuts import render, redirect
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
        note = (request.POST.get('withdraw_note') or '').strip()
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
    breakdown_by_barber = appts_month_done.values('barber__id', 'barber__display_name', 'barber__username').annotate(
        count=Count('id'),
        total_value=Sum('service__price')
    ).order_by('-total_value')

    # CSV export (month-to-date paid sales)
    if request.GET.get('export') == 'csv':
        rows = sales_month.filter(status='paid').select_related('barber').order_by('-created_at')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="financas_mensal.csv"'
        writer = csv.writer(response)
        # Header differs for admin vs barber view
        if is_admin:
            writer.writerow(['Data', 'Hora', 'Barbeiro', 'Valor', 'Pagamento', 'Status'])
        else:
            writer.writerow(['Data', 'Hora', 'Valor', 'Pagamento', 'Status'])
        for s in rows:
            date_str = timezone.localtime(s.created_at).strftime('%d/%m/%Y')
            time_str = timezone.localtime(s.created_at).strftime('%H:%M')
            if is_admin:
                writer.writerow([
                    date_str,
                    time_str,
                    getattr(s.barber, 'display_name', None) or getattr(s.barber, 'username', ''),
                    str(s.amount),
                    s.get_payment_method_display(),
                    s.status,
                ])
            else:
                writer.writerow([
                    date_str,
                    time_str,
                    str(s.amount),
                    s.get_payment_method_display(),
                    s.status,
                ])
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
                done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=utc_beg, start_datetime__lt=utc_end)
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
                done_qs = Appointment.objects.filter(status=Appointment.STATUS_DONE, start_datetime__gte=utc_beg, start_datetime__lt=utc_end)
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
