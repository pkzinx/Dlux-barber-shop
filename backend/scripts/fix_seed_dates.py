from django.utils import timezone
from appointments.models import Appointment
from users.models import User
from django.test.client import RequestFactory
from users.views import finances_chart_data
import datetime

print('Running fix_seed_dates...')

# Choose target dates before 2025-12-09
this_week_dates = [
    datetime.date(2025, 12, 4),
    datetime.date(2025, 12, 5),
    datetime.date(2025, 12, 6),
]
last_week_dates = [
    datetime.date(2025, 11, 25),
    datetime.date(2025, 11, 27),
    datetime.date(2025, 11, 28),
]

tz = timezone.get_current_timezone()

# Fetch appointments seeded earlier (client_name startswith 'Teste')
qs = list(Appointment.objects.filter(client_name__startswith='Teste').order_by('id'))
print('Found', len(qs), 'appointments to adjust')

if not qs:
    print('No appointments found matching criteria. Exiting.')
else:
    # assign first three to this_week_dates, next three to last_week_dates
    idx = 0
    for i, appt in enumerate(qs[:6]):
        if i < 3:
            date_target = this_week_dates[i % len(this_week_dates)]
        else:
            date_target = last_week_dates[i % len(last_week_dates)]
        # random-ish time slot deterministic
        hour = 9 + (i * 2) % 8
        minute = [0, 15, 30, 45][i % 4]
        local_dt = datetime.datetime(date_target.year, date_target.month, date_target.day, hour, minute)
        local_dt = timezone.make_aware(local_dt, tz)
        start_utc = local_dt.astimezone(datetime.timezone.utc)
        end_local = local_dt + datetime.timedelta(minutes=(appt.service.duration_minutes or 30))
        end_utc = end_local.astimezone(datetime.timezone.utc)
        appt.start_datetime = start_utc
        appt.end_datetime = end_utc
        appt.status = Appointment.STATUS_DONE
        appt.save()
        print('Updated', appt.client_name, '->', local_dt.isoformat())

    # Now call the view to get JSON for range=30 and compare=1
    rf = RequestFactory()
    req = rf.get('/painel/financas/chart-data/', {'range': '30', 'compare': '1'})
    # set an authenticated user
    user = User.objects.filter(is_active=True).first()
    if not user:
        print('No user to authenticate as; skipping view test.')
    else:
        req.user = user
        resp = finances_chart_data(req)
        try:
            print('finances_chart_data response:', resp.content.decode('utf-8')[:1000])
        except Exception as e:
            print('Error printing response:', e)

print('Done')
