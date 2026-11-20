import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0010_guardado_reporte_publicacion_oculta'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MejorAmigo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_el', models.DateTimeField(auto_now_add=True)),
                ('amigo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mejor_amigo_de', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mejores_amigos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('user', 'amigo'), name='mejor_amigo_unico')],
            },
        ),
        migrations.CreateModel(
            name='Silenciado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_el', models.DateTimeField(auto_now_add=True)),
                ('silenciado', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='silenciado_por', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='silencios', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('user', 'silenciado'), name='silenciado_unico')],
            },
        ),
    ]
