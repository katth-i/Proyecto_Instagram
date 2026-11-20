"""
Convierte en moderadores (administradores) a los usuarios indicados en la
variable de entorno MODERADORES, separados por comas. Ejemplo en Render:

    MODERADORES = kate_,monse

Se ejecuta en cada despliegue (Build Command). No crea cuentas ni toca contraseñas:
cada moderador entra con su cuenta normal de Fotitos.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Da permisos de moderador a los usuarios de la variable MODERADORES'

    def handle(self, *args, **options):
        nombres = [n.strip().lstrip('@') for n in os.environ.get('MODERADORES', '').split(',') if n.strip()]
        if not nombres:
            self.stdout.write('MODERADORES está vacío: no se cambió nada.')
            return
        for nombre in nombres:
            usuario = User.objects.filter(username__iexact=nombre).first()
            if usuario is None:
                self.stdout.write(self.style.WARNING(f'No existe el usuario "{nombre}" (¿ya se registró?)'))
                continue
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save(update_fields=['is_staff', 'is_superuser'])
            self.stdout.write(self.style.SUCCESS(f'{usuario.username} ahora es moderador'))
