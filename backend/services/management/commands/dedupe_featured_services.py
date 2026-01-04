from django.core.management.base import BaseCommand
from django.db.models import Q
from services.models import Service


class Command(BaseCommand):
    help = "Desativa duplicatas dos serviços principais (Corte de Cabelo, Barba, Corte e Barba), mantendo apenas um ativo."

    def handle(self, *args, **options):
        groups = {
            'corte_de_cabelo': Q(title__iexact='corte') | Q(title__iexact='corte de cabelo'),
            'barba': Q(title__iexact='barba'),
            'corte_barba': Q(title__iexact='corte + barba') | Q(title__iexact='corte e barba') | Q(title__iexact='corte & barba'),
        }

        total_inactivated = 0
        for name, q in groups.items():
            qs = Service.objects.filter(q).order_by('id')
            count = qs.count()
            if count <= 1:
                self.stdout.write(self.style.NOTICE(f"Grupo '{name}': {count} registro(s), nada a fazer"))
                continue

            active_qs = [s for s in qs if s.active]
            if active_qs:
                primary = active_qs[0]
            else:
                primary = qs[0]

            inactivated_here = 0
            for s in qs:
                if s.id == primary.id:
                    continue
                if s.active:
                    s.active = False
                    s.save(update_fields=['active'])
                    inactivated_here += 1

            total_inactivated += inactivated_here
            self.stdout.write(self.style.SUCCESS(
                f"Grupo '{name}': mantendo Service id={primary.id} ativo; desativados {inactivated_here} duplicata(s)"
            ))

        self.stdout.write(self.style.SUCCESS(f"Total desativado: {total_inactivated}"))
