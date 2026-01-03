import random
import datetime
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from users.models import User
from appointments.models import Appointment
from services.models import Service
from sales.models import Sale, Withdrawal
from audit.models import AuditLog

def run():
    print("Iniciando limpeza e geração de dados...")
    
    with transaction.atomic():
        # 1. Clear Data
        Appointment.objects.all().delete()
        Sale.objects.all().delete()
        Withdrawal.objects.all().delete()
        AuditLog.objects.all().delete()
        print("Dados antigos removidos.")

        # 2. Setup
        # Referência: Hoje é 02/01/2026
        today = datetime.date(2026, 1, 2)
        
        barbers = list(User.objects.filter(role='barber'))
        if not barbers:
            print("ERRO: Nenhum barbeiro encontrado com role='barber'.")
            return

        services = list(Service.objects.all())
        if not services:
            # Fallback if no services
            s = Service.objects.create(title="Corte Masculino", price=Decimal("35.00"), duration_minutes=30)
            services = [s]

        clients = ["João Silva", "Maria Oliveira", "Pedro Santos", "Ana Costa", "Lucas Pereira", 
                   "Fernanda Lima", "Gabriel Souza", "Amanda Rocha", "Rafael Dias", "Beatriz Alves",
                   "Carlos Eduardo", "Patricia Melo", "Ricardo Gomes", "Larissa Martins", "Felipe Nogueira"]
        
        # Track client usage to respect "max 2 times in 15 days" rule
        client_usage = {c: 0 for c in clients}

        summary = {}
        
        # 3. Appointments
        for barber in barbers:
            # 3 to 4 appointments
            num_appts = random.randint(3, 4)
            barber_total_value = Decimal(0)
            
            # Generate random dates in the next 15 days (02/01 to 17/01)
            # We shuffle a list of offsets to ensure variety if possible
            day_offsets = list(range(1, 16)) # 1 to 15 days ahead
            random.shuffle(day_offsets)
            
            created_count = 0
            for i in range(num_appts):
                if i >= len(day_offsets): break # Should not happen with 3-4 appts and 15 days
                
                # Pick client
                available_clients = [c for c, count in client_usage.items() if count < 2]
                if not available_clients:
                    available_clients = clients # Fallback
                
                client = random.choice(available_clients)
                client_usage[client] += 1
                
                # Date and Time
                offset = day_offsets[i]
                appt_date = today + datetime.timedelta(days=offset)
                
                # Random hour 09:00 to 18:00
                hour = random.randint(9, 18)
                minute = random.choice([0, 30])
                
                start_dt = datetime.datetime.combine(appt_date, datetime.time(hour, minute))
                start_dt = timezone.make_aware(start_dt)
                
                service = random.choice(services)
                end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)
                
                Appointment.objects.create(
                    barber=barber,
                    client_name=client,
                    client_phone="11999999999",
                    service=service,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    status='scheduled' # Default to scheduled as requested for "next 15 days"
                )
                barber_total_value += service.price
                created_count += 1
                
            summary[barber.username] = {
                'count': created_count,
                'total': barber_total_value
            }

        # 4. Withdrawals
        # Total ~150, different categories, different days
        withdrawal_categories = ["Outros", "Despesas", "Luz", "Fornecedor"]
        current_withdrawal_total = Decimal(0)
        target_withdrawal = Decimal(150)
        
        withdrawals_created = 0
        
        while current_withdrawal_total < target_withdrawal:
            barber = random.choice(barbers)
            amount = Decimal(random.choice([20, 30, 40, 50]))
            
            # Avoid exceeding too much
            if current_withdrawal_total + amount > target_withdrawal + Decimal(10):
                if target_withdrawal - current_withdrawal_total > 5:
                    amount = target_withdrawal - current_withdrawal_total
                else:
                    break
            
            category = random.choice(withdrawal_categories)
            
            # Random date around today
            offset = random.randint(0, 5)
            w_date = today + datetime.timedelta(days=offset)
            w_dt = datetime.datetime.combine(w_date, datetime.time(10, 0))
            w_dt = timezone.make_aware(w_dt)
            
            w = Withdrawal.objects.create(
                user=barber,
                amount=amount,
                note=category
                # created_at set below
            )
            # Hack to set created_at since auto_now_add overrides it on create
            w.created_at = w_dt
            w.save()
            
            current_withdrawal_total += amount
            withdrawals_created += 1

    # Output Summary
    print("\n=== RESUMO GERAL ===")
    for b_name, data in summary.items():
        print(f"Barbeiro {b_name}: {data['count']} agendamentos (Valor est. R$ {data['total']})")
    
    print(f"\nRetiradas: {withdrawals_created} lançamentos, Total R$ {current_withdrawal_total}")
    print("====================")

if __name__ == '__main__':
    run()
