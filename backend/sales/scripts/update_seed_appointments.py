from django.utils import timezone
import datetime
import random
from users.models import User
from appointments.models import Appointment

tz = timezone.get_current_timezone()
base_date = datetime.date(2025, 12, 15)

alafy = User.objects.filter(username__iexact='alafy', role='barber').first()
rikelv = User.objects.filter(username__iexact='rikelv', role='barber').first()
third = (
    User.objects.filter(role='barber')
    .exclude(username__iexact='alafy')
    .exclude(username__iexact='rikelv')
    .order_by('id')
    .first()
)

barbers = [b for b in [alafy, rikelv, third] if b]
seed = list(Appointment.objects.filter(client_name__startswith='Seed').order_by('start_datetime'))

seed_done_today = [a for a in seed if a.status == 'done' and timezone.localtime(a.start_datetime).date() == base_date]
seed_future = [a for a in seed if a.status == 'scheduled' and timezone.localtime(a.start_datetime).date() > base_date]

assign_groups = {}
for i, b in enumerate(barbers):
    assign_groups[b] = {
        'done': seed_done_today[i * 2:(i + 1) * 2],
        'future': seed_future[i * 3:(i + 1) * 3],
    }

first_names = ['Joao','Pedro','Lucas','Mateus','Gustavo','Bruno','Felipe','Rafael','Tiago','Diego','Henrique','Leandro']
last_names = ['Lima','Santos','Almeida','Souza','Oliveira','Pereira','Ferreira','Araujo','Carvalho','Barbosa','Rocha','Mendes']
random.shuffle(first_names)
random.shuffle(last_names)
names = [first_names[i % len(first_names)] + ' ' + last_names[(i * 2) % len(last_names)] for i in range(15)]

def gen_phone():
    return '11' + ''.join(str(random.randint(0, 9)) for _ in range(9))

phones_unique = [gen_phone() for _ in range(10)]
phones = []
for i in range(5):
    phones.append(phones_unique[i])
    phones.append(phones_unique[i])
phones.extend(phones_unique[5:10])
random.shuffle(phones)

idx = 0
for b in barbers:
    for a in assign_groups[b]['done']:
        a.barber = b
        a.client_name = names[idx]
        a.client_phone = phones[idx]
        a.save(update_fields=['barber', 'client_name', 'client_phone'])
        idx += 1
    for a in assign_groups[b]['future']:
        a.barber = b
        a.client_name = names[idx]
        a.client_phone = phones[idx]
        a.save(update_fields=['barber', 'client_name', 'client_phone'])
        idx += 1

print('updated', idx)
