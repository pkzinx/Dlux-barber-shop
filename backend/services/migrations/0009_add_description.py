from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0008_alter_service_options_service_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
    ]
