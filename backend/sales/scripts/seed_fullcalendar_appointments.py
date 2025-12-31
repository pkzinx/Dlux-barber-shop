"""Seed script: cria 2 agendamentos por barbeiro para aparecerem no FullCalendar.

Cria agendamentos com status 'scheduled' para hoje (09/12/2025) em dois horários
por barbeiro. Usa o primeiro serviço disponível ou cria um serviço placeholder.
"""
from django.utils import timezone
import datetime
import random
from users.models import User
from appointments.models import Appointment
from services.models import Service


def main():
    tz = timezone.get_current_timezone()
    # Base date (inclusive) requested: 09/12/2025
    start_base = datetime.date(2025, 12, 9)
    # Range in days after start_base to distribute appointments (inclusive)
    RANGE_DAYS = 21

    # Remove previous seed entries to avoid duplicates
    old_qs = Appointment.objects.filter(client_name__startswith='Seed ')
    removed = old_qs.count()
    if removed:
        old_qs.delete()
        print(f'Removed {removed} old seed appointments')

    # Ensure a service exists
    svc = Service.objects.filter(active=True).first()
    if not svc:
        svc = Service.objects.create(title='Corte (seed)', price=50.00, duration_minutes=60, active=True)
        print('Created placeholder service:', svc.id)

    barbers = list(User.objects.filter(role=User.BARBER).order_by('id'))
    if not barbers:
        print('No barbers found. Create at least one barber user before seeding.')
        return

    created = []
    # Working hours choices (avoid lunch at 12)
    hours_pool = [9, 10, 11, 13, 14, 15, 16]
    for b in barbers:
        # pick two distinct day offsets within the range
        offsets = random.sample(range(0, RANGE_DAYS), 2)
        for idx, off in enumerate(offsets):
            day = start_base + datetime.timedelta(days=off)
            # pick a time slot (different times preferred)
            hh = hours_pool[idx % len(hours_pool)] if idx < len(hours_pool) else random.choice(hours_pool)
            start_dt = datetime.datetime(year=day.year, month=day.month, day=day.day, hour=hh, minute=0, second=0)
            start_dt = timezone.make_aware(start_dt, tz)
            end_dt = start_dt + datetime.timedelta(minutes=(svc.duration_minutes or 60))
            a = Appointment.objects.create(
                barber=b,
                client_name=f'Seed {b.username}',
                client_phone='999999999',
                service=svc,
                start_datetime=start_dt,
                end_datetime=end_dt,
                status=Appointment.STATUS_SCHEDULED,
            )
            created.append(a)
            print(f'Created appointment for {b.username} at {start_dt.isoformat()} (id={a.id})')

    print('Total created:', len(created))


if __name__ == '__main__':
    main()
