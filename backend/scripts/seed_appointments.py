from django.utils import timezone
from appointments.models import Appointment
from services.models import Service
from users.models import User
import random
import datetime

now = timezone.localtime()

def ensure_services():
    services = list(Service.objects.all())
    if len(services) < 3:
        samples = [
            ('Corte masculino', '40.00', 30),
            ('Barba', '25.00', 20),
            ('Corte + Barba', '60.00', 50),
            ('Penteado', '50.00', 45),
        ]
        for title, price, minutes in samples:
            if not Service.objects.filter(title=title).exists():
                Service.objects.create(title=title, price=price, duration_minutes=minutes)
    return list(Service.objects.all())


def ensure_barbers():
    barbers = list(User.objects.filter(role=User.BARBER))
    if not barbers:
        # create a test barber
        b = User.objects.create_user(username='barbeiro_demo', password='demo123', role=User.BARBER, display_name='Barbeiro Demo')
        barbers = [b]
    return barbers


services = ensure_services()
barbers = ensure_barbers()

# Helper to create an appointment at local datetime
def create_appt(local_dt, service, barber, client_name):
    start = local_dt
    end = start + datetime.timedelta(minutes=service.duration_minutes or 30)
    # convert to UTC-aware datetimes for DB
    start_utc = start.astimezone(datetime.timezone.utc)
    end_utc = end.astimezone(datetime.timezone.utc)
    appt = Appointment.objects.create(
        barber=barber,
        client_name=client_name,
        client_phone='11999999999',
        service=service,
        start_datetime=start_utc,
        end_datetime=end_utc,
        status=Appointment.STATUS_DONE
    )
    print('Created', appt)
    return appt

# Determine current week Monday
today = now.date()
start_of_week = today - datetime.timedelta(days=today.weekday())

# this week random 3 days
this_week_days = random.sample(range(0, 7), 3)
# last week random 3 days
last_week_start = start_of_week - datetime.timedelta(days=7)
last_week_days = random.sample(range(0, 7), 3)

# Random times between 9:00 and 17:00
for d in this_week_days:
    day = start_of_week + datetime.timedelta(days=d)
    hour = random.randint(9, 16)
    minute = random.choice([0, 15, 30, 45])
    dt_local = datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=now.tzinfo)
    svc = random.choice(services)
    br = random.choice(barbers)
    create_appt(dt_local, svc, br, client_name=f'Teste Hoje {d}')

for d in last_week_days:
    day = last_week_start + datetime.timedelta(days=d)
    hour = random.randint(9, 16)
    minute = random.choice([0, 15, 30, 45])
    dt_local = datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=now.tzinfo)
    svc = random.choice(services)
    br = random.choice(barbers)
    create_appt(dt_local, svc, br, client_name=f'Teste SemanaPassada {d}')

print('Seeding complete')
