import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cuentas', '0009_perfil_username_cambiado_el'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='publicacion',
            name='oculta',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='Guardado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_el', models.DateTimeField(auto_now_add=True)),
                ('publicacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardada_por', to='cuentas.publicacion')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('user', 'publicacion'), name='guardado_unico')],
            },
        ),
        migrations.CreateModel(
            name='Reporte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('motivo', models.CharField(choices=[('spam', 'Spam o publicidad'), ('inapropiado', 'Desnudos o contenido inapropiado'), ('acoso', 'Acoso o bullying'), ('violencia', 'Violencia u odio'), ('falso', 'Información falsa'), ('otro', 'Otro motivo')], max_length=20)),
                ('detalle', models.CharField(blank=True, max_length=300)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('resuelto', 'Resuelto (se tomó acción)'), ('descartado', 'Descartado (no había problema)')], default='pendiente', max_length=20)),
                ('creado_el', models.DateTimeField(auto_now_add=True)),
                ('publicacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to='cuentas.publicacion')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes_hechos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('publicacion', 'usuario'), name='reporte_unico')],
            },
        ),
    ]
