from django.utils import timezone
import datetime
import random
from users.models import User
from services.models import Service
from appointments.models import Appointment

tz = timezone.get_current_timezone()

# Ensure a service exists
svc = Service.objects.filter(active=True).first() or Service.objects.first()
if not svc:
    svc = Service.objects.create(title='Corte (seed)', price=50.00, duration_minutes=45, active=True)

barbers = list(User.objects.filter(role=User.BARBER).order_by('id'))
hours = [9, 10, 11, 13, 14, 15, 16]

# Build names and phones (max repetition per number: 2)
first_names = ['Joao','Pedro','Lucas','Mateus','Gustavo','Bruno','Felipe','Rafael','Tiago','Diego','Henrique','Leandro','Paulo','Vitor','Caio','Igor','Daniel']
last_names = ['Lima','Santos','Almeida','Souza','Oliveira','Pereira','Ferreira','Araujo','Carvalho','Barbosa','Rocha','Mendes','Dias','Nogueira','Rezende']
random.shuffle(first_names)
random.shuffle(last_names)

def gen_name(i: int) -> str:
    return f"{first_names[i % len(first_names)]} {last_names[(i * 2) % len(last_names)]}"

def gen_phone_pool(count_unique: int = 20):
    uniques = ['11' + ''.join(str(random.randint(0, 9)) for _ in range(9)) for _ in range(count_unique)]
    pool = []
    for i in range(10):
        pool.append(uniques[i])
        pool.append(uniques[i])
    pool.extend(uniques[10:count_unique])
    random.shuffle(pool)
    return pool

phones_pool = gen_phone_pool(30)
phone_idx = 0
name_idx = 0

created = 0
for b in barbers:
    # 4 concluded appointments per barber, random days between 1 and 24
    days = random.sample(range(1, 25), 4)
    for dd in days:
        hh = random.choice(hours)
        start_local = timezone.make_aware(datetime.datetime(2025, 12, dd, hh, 0), tz)
        end_local = start_local + datetime.timedelta(minutes=(svc.duration_minutes or 45))
        name = gen_name(name_idx); name_idx += 1
        phone = phones_pool[phone_idx % len(phones_pool)]; phone_idx += 1
        Appointment.objects.create(
            barber=b,
            client_name=name,
            client_phone=phone,
            service=svc,
            start_datetime=start_local,
            end_datetime=end_local,
            status=Appointment.STATUS_DONE,
        )
        created += 1

print('Seeded concluded appointments for December:', created)
