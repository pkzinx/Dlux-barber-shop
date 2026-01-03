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
    print("Iniciando limpeza e geração de dados (26/12/25 a 10/01/26)...")
    
    with transaction.atomic():
        # 1. Clear Data
        Appointment.objects.all().delete()
        Sale.objects.all().delete()
        Withdrawal.objects.all().delete()
        AuditLog.objects.all().delete()
        print("Dados antigos removidos.")

        # 2. Setup
        start_date = datetime.date(2025, 12, 26)
        end_date = datetime.date(2026, 1, 10)
        days_range = (end_date - start_date).days + 1
        
        barbers = list(User.objects.filter(role='barber'))
        if not barbers:
            print("ERRO: Nenhum barbeiro encontrado.")
            # Try to create one for testing if none exist
            return

        services = list(Service.objects.all())
        if not services:
            s = Service.objects.create(title="Corte Masculino", price=Decimal("35.00"), duration_minutes=30)
            services = [s]

        # Core clients for consistency (Phone is the key)
        core_clients = [
            {"name": "João Silva", "phone": "11911111111"},
            {"name": "Maria Oliveira", "phone": "11922222222"},
            {"name": "Carlos Souza", "phone": "11933333333"},
            {"name": "Ana Lima", "phone": "11944444444"},
            {"name": "Pedro Santos", "phone": "11955555555"},
            {"name": "Lucas Pereira", "phone": "11966666666"},
            {"name": "Fernanda Costa", "phone": "11977777777"},
            {"name": "Rafael Dias", "phone": "11988888888"},
        ]
        
        payment_methods = ['cash', 'pix', 'card']

        # 3. Appointments & Sales
        total_appts = 0
        for barber in barbers:
            # At least 8 appointments per barber
            num_appts = random.randint(8, 15)
            print(f"Gerando {num_appts} agendamentos para {barber.username}...")
            
            for _ in range(num_appts):
                # Determine Client Strategy
                r = random.random()
                if r < 0.7:
                    # 70% chance: Core client (Consistent Name & Phone)
                    c = random.choice(core_clients)
                    client_name = c["name"]
                    client_phone = c["phone"]
                elif r < 0.85:
                    # 15% chance: Core client phone, but variation in name (Tests grouping by phone)
                    c = random.choice(core_clients)
                    variations = [c["name"].lower(), c["name"].upper(), c["name"].split()[0]]
                    client_name = random.choice(variations)
                    client_phone = c["phone"]
                else:
                    # 15% chance: Completely new random client
                    client_name = f"Cliente {random.randint(100, 999)}"
                    client_phone = f"119{random.randint(10000000, 99999999)}"

                # Random Date
                days_offset = random.randint(0, days_range - 1)
                appt_date = start_date + datetime.timedelta(days=days_offset)
                
                # Random Time
                hour = random.randint(9, 19)
                minute = random.choice([0, 30])
                start_dt = datetime.datetime.combine(appt_date, datetime.time(hour, minute))
                start_dt = timezone.make_aware(start_dt)
                
                service = random.choice(services)
                end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)

                # Create Appointment
                appt = Appointment.objects.create(
                    barber=barber,
                    client_name=client_name,
                    client_phone=client_phone,
                    service=service,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    status='done',
                    notes="Gerado automaticamente v4"
                )

                # Create Sale
                sale = Sale.objects.create(
                    barber=barber,
                    appointment=appt,
                    service=service,
                    description=service.title,
                    amount=service.price,
                    payment_method=random.choice(payment_methods),
                    status='paid'
                )
                sale.created_at = start_dt
                sale.save()
                total_appts += 1

        # 4. Withdrawals
        withdrawal_reasons = [
            "Lanche", "Gasolina", "Material de Limpeza", "Adiantamento", 
            "Manutenção Equipamento", "Conta de Luz", "Internet", "Água", 
            "Fornecedor (Produtos)", "Marketing"
        ]
        
        num_withdrawals = random.randint(15, 25)
        print(f"Gerando {num_withdrawals} retiradas...")
        
        for _ in range(num_withdrawals):
            barber = random.choice(barbers)
            amount = Decimal(random.choice([15, 25, 35, 50, 100]))
            reason = random.choice(withdrawal_reasons)
            
            days_offset = random.randint(0, days_range - 1)
            w_date = start_date + datetime.timedelta(days=days_offset)
            w_dt = timezone.make_aware(datetime.datetime.combine(w_date, datetime.time(14, 0)))
            
            w = Withdrawal.objects.create(
                user=barber,
                amount=amount,
                note=reason
            )
            w.created_at = w_dt
            w.save()

    print(f"\nConcluído! {total_appts} agendamentos e {num_withdrawals} retiradas criados.")

if __name__ == '__main__':
    run()
