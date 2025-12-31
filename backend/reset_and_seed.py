import os
import random
import datetime
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from users.models import User
from appointments.models import Appointment, Service
from sales.models import Withdrawal

def run():
    print("Apagando todos os agendamentos existentes...")
    Appointment.objects.all().delete()
    
    # We will assume we want to keep existing withdrawals unless specified otherwise, 
    # but since we are adding 200, maybe we should just add. 
    # However, for a clean test state of "reset", maybe clearing is better? 
    # The prompt says "reset" (in my thought process) but user said "apague todos os agendamentos".
    # I will stick to deleting appointments only.
    
    start_date = datetime.date(2025, 12, 15)
    end_date = datetime.date(2025, 12, 31)
    
    barbers = list(User.objects.filter(role='barber'))
    if not barbers:
        print("Nenhum barbeiro encontrado.")
        return

    services = list(Service.objects.all())
    if not services:
        print("Nenhum serviço encontrado.")
        return

    # Helper to check overlap
    # occupied[barber_id] = [(start, end), ...]
    occupied = {b.id: [] for b in barbers}

    for barber in barbers:
        num_appts = random.randint(3, 6)
        print(f"Gerando {num_appts} agendamentos para {barber.username}...")
        
        for _ in range(num_appts):
            # Try finding a slot
            attempts = 0
            while attempts < 50:
                attempts += 1
                
                # Random date
                days_diff = (end_date - start_date).days
                random_days = random.randint(0, days_diff)
                appt_date = start_date + datetime.timedelta(days=random_days)
                
                # Random time
                appt_hour = random.randint(9, 19)
                appt_minute = random.choice([0, 30])
                
                start_dt = datetime.datetime.combine(appt_date, datetime.time(appt_hour, appt_minute))
                if timezone.is_naive(start_dt):
                    start_dt = timezone.make_aware(start_dt)
                
                service = random.choice(services)
                duration = service.duration_minutes
                end_dt = start_dt + datetime.timedelta(minutes=duration)
                
                # Check overlap locally
                conflict = False
                for s, e in occupied[barber.id]:
                    # Overlap if (start < e) and (end > s)
                    if not (end_dt <= s or start_dt >= e):
                        conflict = True
                        break
                
                if not conflict:
                    # No conflict, save it
                    occupied[barber.id].append((start_dt, end_dt))
                    
                    # Status logic: 
                    # "Hoje" is 31/12/2025.
                    # Let's say "now" is 12:00 on 31/12/2025.
                    now_simulated = timezone.make_aware(datetime.datetime(2025, 12, 31, 12, 0, 0))
                    
                    if start_dt < now_simulated:
                        status = Appointment.STATUS_DONE
                    else:
                        status = Appointment.STATUS_SCHEDULED
                    
                    appt = Appointment(
                        barber=barber,
                        client_name=f"Cliente {random.randint(1, 100)}",
                        client_phone=f"629{random.randint(80000000, 99999999)}",
                        service=service,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        status=status,
                        notes="Gerado automaticamente"
                    )
                    appt.save()
                    break
    
    # Create Withdrawals
    print("Gerando retiradas (Total R$ 200.00)...")
    remaining = Decimal('200.00')
    withdrawal_reasons = ["Lanche", "Gasolina", "Adiantamento", "Material"]
    
    while remaining > 0:
        amount = Decimal(random.choice(['20.00', '30.00', '50.00']))
        if amount > remaining:
            amount = remaining
        
        remaining -= amount
        
        barber = random.choice(barbers)
        
        # Date: Random in the period
        days_diff = (end_date - start_date).days
        random_days = random.randint(0, days_diff) # up to 15 days
        # But maybe limit to 15 days? 
        # Actually random in [0, 15] is fine.
        w_date = start_date + datetime.timedelta(days=random.randint(0, 15))
        w_dt = datetime.datetime.combine(w_date, datetime.time(12, 0))
        if timezone.is_naive(w_dt):
            w_dt = timezone.make_aware(w_dt)
            
        w = Withdrawal.objects.create(
            user=barber,
            amount=amount,
            note=random.choice(withdrawal_reasons)
        )
        # Override created_at
        w.created_at = w_dt
        w.save()

    print("Concluído!")

if __name__ == '__main__':
    run()
