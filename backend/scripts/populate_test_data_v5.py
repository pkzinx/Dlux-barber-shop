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
    print("Iniciando limpeza e geração de dados v5 (26/12/25 a 10/01/26)...")
    
    # "Today" is 2026-01-03
    today_date = datetime.date(2026, 1, 3)

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
            return

        services = list(Service.objects.all())
        if not services:
            s = Service.objects.create(title="Corte Masculino", price=Decimal("35.00"), duration_minutes=30)
            services = [s]

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
        sales_count = 0
        
        # Track occupied slots per barber to avoid overlap: barber_username -> list of (start_dt, end_dt)
        occupied_slots = {}

        for barber in barbers:
            occupied_slots[barber.username] = []
            num_appts = random.randint(8, 15)
            print(f"Gerando {num_appts} agendamentos para {barber.username}...")
            
            created_for_barber = 0
            attempts = 0
            max_attempts = 100 # Avoid infinite loop
            
            while created_for_barber < num_appts and attempts < max_attempts:
                attempts += 1
                
                # Determine Client
                r = random.random()
                if r < 0.7:
                    c = random.choice(core_clients)
                    client_name = c["name"]
                    client_phone = c["phone"]
                elif r < 0.85:
                    c = random.choice(core_clients)
                    variations = [c["name"].lower(), c["name"].upper(), c["name"].split()[0]]
                    client_name = random.choice(variations)
                    client_phone = c["phone"]
                else:
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

                # Check overlap
                overlap = False
                for o_start, o_end in occupied_slots[barber.username]:
                    # Overlap if (StartA < EndB) and (EndA > StartB)
                    if start_dt < o_end and end_dt > o_start:
                        overlap = True
                        break
                
                if overlap:
                    continue

                # No overlap, proceed
                occupied_slots[barber.username].append((start_dt, end_dt))

                # Determine Status based on "Today" (2026-01-03)
                if appt_date < today_date:
                    status = 'done'
                else:
                    status = 'scheduled'

                # Create Appointment
                try:
                    appt = Appointment.objects.create(
                        barber=barber,
                        client_name=client_name,
                        client_phone=client_phone,
                        service=service,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        status=status,
                        notes="Gerado v5"
                    )

                    # Create Sale ONLY if DONE
                    if status == 'done':
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
                        sales_count += 1
                    
                    total_appts += 1
                    created_for_barber += 1
                except Exception as e:
                    print(f"Erro ao criar agendamento: {e}")


        # 4. Withdrawals
        # Categories requested: Itens básicos, Aluguel/Agua/Luz, Produtos freezer, Outros
        
        withdrawal_categories = {
            "Itens básicos": ["Papel higiênico", "Copos descartáveis", "Café e açúcar", "Produtos de limpeza"],
            "Aluguel/Agua/Luz": ["Conta de Luz", "Conta de Água", "Aluguel do Mês", "Taxa de Condomínio"],
            "Produtos freezer": ["Refrigerantes", "Cervejas", "Gelo", "Energéticos"],
            "Outros": ["Gasolina", "Manutenção cadeira", "Lanche da tarde", "Uber"]
        }
        
        category_totals = {cat: Decimal(0) for cat in withdrawal_categories}
        MAX_PER_CATEGORY = Decimal(50)
        
        num_withdrawals_target = random.randint(15, 25)
        created_withdrawals = 0
        
        print(f"Gerando retiradas (Meta: {num_withdrawals_target}, Max R$ 50/categoria)...")
        
        # Withdrawals only up to today
        days_range_past = (today_date - start_date).days + 1
        
        attempts = 0
        while created_withdrawals < num_withdrawals_target and attempts < 200:
            attempts += 1
            barber = random.choice(barbers)
            
            # Smaller amounts to fit within 50 per category
            amount = Decimal(random.choice([5, 10, 15, 20]))
            
            # Pick a category that has room
            available_cats = [cat for cat, total in category_totals.items() if total + amount <= MAX_PER_CATEGORY]
            
            if not available_cats:
                # No category fits this amount
                continue
            
            category = random.choice(available_cats)
            category_totals[category] += amount
            
            detail = random.choice(withdrawal_categories[category])
            
            # Format: [Category] Detail
            final_note = f"[{category}] {detail}"
            
            days_offset = random.randint(0, days_range_past - 1)
            w_date = start_date + datetime.timedelta(days=days_offset)
            w_dt = timezone.make_aware(datetime.datetime.combine(w_date, datetime.time(14, 0)))
            
            w = Withdrawal.objects.create(
                user=barber,
                amount=amount,
                note=final_note
            )
            w.created_at = w_dt
            w.save()
            created_withdrawals += 1

    print(f"\nConcluído! {total_appts} agendamentos ({sales_count} concluídos/vendas) e {created_withdrawals} retiradas criados.")
    print("Totais por Categoria:")
    for cat, total in category_totals.items():
        print(f"  - {cat}: R$ {total}")

if __name__ == '__main__':
    run()
