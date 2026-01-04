from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from services.models import Service
from appointments.models import Appointment
from sales.models import Sale
from services.views import trigger_revalidation


class Command(BaseCommand):
    help = "Mescla duplicatas dos serviços principais: reatribui agendamentos e vendas ao serviço primário e remove duplicados."

    def handle(self, *args, **options):
        groups = {
            'corte_de_cabelo': Q(title__iexact='corte') | Q(title__iexact='corte de cabelo'),
            'barba': Q(title__iexact='barba'),
            'corte_barba': Q(title__iexact='corte + barba') | Q(title__iexact='corte e barba') | Q(title__iexact='corte & barba'),
        }

        total_deleted = 0
        with transaction.atomic():
            for name, q in groups.items():
                qs = list(Service.objects.filter(q).order_by('id'))
                if len(qs) <= 1:
                    self.stdout.write(self.style.NOTICE(f"Grupo '{name}': {len(qs)} registro(s), nada a mesclar"))
                    continue

                # define primário: primeiro ativo, senão o de menor id
                primary = next((s for s in qs if s.active), qs[0])
                self.stdout.write(self.style.NOTICE(f"Grupo '{name}': primário id={primary.id} ({primary.title})"))

                for s in qs:
                    if s.id == primary.id:
                        continue
                    # reatribui referências
                    appt_count = Appointment.objects.filter(service=s).count()
                    if appt_count:
                        Appointment.objects.filter(service=s).update(service=primary)
                        self.stdout.write(self.style.SUCCESS(f"  - Reatribuidos {appt_count} agendamentos do serviço id={s.id} para id={primary.id}"))
                    sale_count = Sale.objects.filter(service=s).count()
                    if sale_count:
                        Sale.objects.filter(service=s).update(service=primary)
                        self.stdout.write(self.style.SUCCESS(f"  - Reatribuidas {sale_count} vendas do serviço id={s.id} para id={primary.id}"))

                    sid = s.id
                    s.delete()
                    total_deleted += 1
                    self.stdout.write(self.style.SUCCESS(f"  - Removido serviço duplicado id={sid}"))

        trigger_revalidation()
        self.stdout.write(self.style.SUCCESS(f"Concluído. Serviços duplicados removidos: {total_deleted}"))
