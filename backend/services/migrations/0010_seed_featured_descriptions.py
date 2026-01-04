from django.db import migrations


def seed_featured_descriptions(apps, schema_editor):
    Service = apps.get_model('services', 'Service')

    desc_hair = 'Realizado em qualquer tecnica de corte de cabelo, incluindo tesouras.'
    desc_beard = 'Aparar o volume ou cortá-la, manutenção do desenho, da hidratação e esfoliação.'
    desc_combo = 'Visual completo: corte preciso e barba tratada com hidratação e acabamento de respeito.'

    # Corte de Cabelo (inclui título "corte")
    for s in Service.objects.filter(title__iexact='corte') | Service.objects.filter(title__iexact='corte de cabelo'):
        if not getattr(s, 'description', ''):
            s.description = desc_hair
            s.save(update_fields=['description'])

    # Barba
    for s in Service.objects.filter(title__iexact='barba'):
        if not getattr(s, 'description', ''):
            s.description = desc_beard
            s.save(update_fields=['description'])

    # Corte e Barba (variações)
    variants = ['corte + barba', 'corte e barba', 'corte & barba']
    for v in variants:
        for s in Service.objects.filter(title__iexact=v):
            if not getattr(s, 'description', ''):
                s.description = desc_combo
                s.save(update_fields=['description'])


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0009_add_description'),
    ]

    operations = [
        migrations.RunPython(seed_featured_descriptions, migrations.RunPython.noop),
    ]
