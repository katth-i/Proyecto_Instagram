from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0008_seguimiento'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='username_cambiado_el',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
