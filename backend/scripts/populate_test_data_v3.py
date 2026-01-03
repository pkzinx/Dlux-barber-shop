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
    print("Iniciando limpeza e geração de dados PASSADOS (27/12/25 a 02/01/26)...")
    
    with transaction.atomic():
        # 1. Clear Data
        Appointment.objects.all().delete()
        Sale.objects.all().delete()
        Withdrawal.objects.all().delete()
        AuditLog.objects.all().delete()
        print("Dados antigos removidos.")

        # 2. Setup
        start_date = datetime.date(2025, 12, 27)
        end_date = datetime.date(2026, 1, 2)
        days_range = (end_date - start_date).days + 1 # Include end_date
        
        barbers = list(User.objects.filter(role='barber'))
        if not barbers:
            print("ERRO: Nenhum barbeiro encontrado com role='barber'.")
            return

        services = list(Service.objects.all())
        if not services:
            # Fallback
            s = Service.objects.create(title="Corte Masculino", price=Decimal("35.00"), duration_minutes=30)
            services = [s]

        clients = ["João Silva", "Maria Oliveira", "Ana Costa", "Lucas Pereira", 
                   "Fernanda Lima", "Gabriel Souza", "Amanda Rocha", "Rafael Dias", "Beatriz Alves",
                   "Carlos Eduardo", "Patricia Melo", "Ricardo Gomes", "Larissa Martins", "Felipe Nogueira"]
        
        client_usage = {c: 0 for c in clients}
        summary = {}
        
        # Payment methods for sales
        payment_methods = ['cash', 'pix', 'card']

        # 3. Appointments & Sales (History)
        for barber in barbers:
            # Generate more volume for history (e.g., 5-8 appts over the week)
            num_appts = random.randint(5, 8)
            barber_total_value = Decimal(0)
            created_count = 0
            
            for _ in range(num_appts):
                # Pick client
                available_clients = [c for c, count in client_usage.items() if count < 2]
                if not available_clients: available_clients = clients
                client = random.choice(available_clients)
                client_usage[client] += 1
                
                # Random Date in range
                days_offset = random.randint(0, days_range - 1)
                appt_date = start_date + datetime.timedelta(days=days_offset)
                
                # Random time
                hour = random.randint(9, 19)
                minute = random.choice([0, 30])
                start_dt = datetime.datetime.combine(appt_date, datetime.time(hour, minute))
                start_dt = timezone.make_aware(start_dt)
                
                service = random.choice(services)
                end_dt = start_dt + datetime.timedelta(minutes=service.duration_minutes)
                
                # Random Phone
                phone_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
                phone = f"119{phone_suffix}"

                # Create DONE appointment
                appt = Appointment.objects.create(
                    barber=barber,
                    client_name=client,
                    client_phone=phone,
                    service=service,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    status='done', # Finalizado
                    notes="Histórico importado"
                )
                
                # Create SALE (Revenue)
                # Important: Sale created_at must match the appointment date for charts to work correctly
                sale = Sale.objects.create(
                    barber=barber,
                    appointment=appt,
                    service=service,
                    description=service.title,
                    amount=service.price,
                    payment_method=random.choice(payment_methods),
                    status='paid'
                )
                # Manually set created_at to match appointment time (simulating past sale)
                sale.created_at = start_dt
                sale.save()

                barber_total_value += service.price
                created_count += 1
                
            summary[barber.username] = {
                'count': created_count,
                'total': barber_total_value
            }

        # 4. Withdrawals with diverse reasons
        withdrawal_reasons = [
            "Lanche", "Gasolina", "Material de Limpeza", "Adiantamento", 
            "Manutenção Equipamento", "Conta de Luz", "Internet", "Água", 
            "Fornecedor (Produtos)", "Marketing"
        ]
        
        current_withdrawal_total = Decimal(0)
        target_withdrawal = Decimal(150)
        withdrawals_created = 0
        
        while current_withdrawal_total < target_withdrawal:
            barber = random.choice(barbers)
            amount = Decimal(random.choice([15, 25, 35, 50]))
            
            if current_withdrawal_total + amount > target_withdrawal + Decimal(10):
                if target_withdrawal - current_withdrawal_total > 5:
                    amount = target_withdrawal - current_withdrawal_total
                else:
                    break
            
            reason = random.choice(withdrawal_reasons)
            
            # Random date in range
            days_offset = random.randint(0, days_range - 1)
            w_date = start_date + datetime.timedelta(days=days_offset)
            w_dt = datetime.datetime.combine(w_date, datetime.time(14, 0))
            w_dt = timezone.make_aware(w_dt)
            
            w = Withdrawal.objects.create(
                user=barber,
                amount=amount,
                note=reason
            )
            w.created_at = w_dt
            w.save()
            
            current_withdrawal_total += amount
            withdrawals_created += 1

    # Output Summary
    print("\n=== RESUMO GERAL (Passado: 27/12 a 02/01) ===")
    for b_name, data in summary.items():
        print(f"Barbeiro {b_name}: {data['count']} atendimentos (Receita R$ {data['total']})")
    
    print(f"\nRetiradas: {withdrawals_created} lançamentos, Total R$ {current_withdrawal_total}")
    print(f"Motivos variados: {', '.join(withdrawal_reasons[:5])}...")
    print("=============================================")

if __name__ == '__main__':
    run()
