from django.core.management.base import BaseCommand
from appointments.models import ClientToken
from appointments.fcm import send_push

class Command(BaseCommand):
    help = 'Envia notificação promocional para todos os dispositivos registrados.'

    def add_arguments(self, parser):
        parser.add_argument('title', type=str, help='Título da notificação')
        parser.add_argument('body', type=str, help='Corpo da mensagem')

    def handle(self, *args, **options):
        title = options['title']
        body = options['body']
        tokens = ClientToken.objects.all()
        count = 0
        self.stdout.write(f"Enviando para {tokens.count()} dispositivos...")

        for t in tokens:
            if send_push(t.token, title, body):
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Sucesso: {count}/{tokens.count()} enviados.'))
