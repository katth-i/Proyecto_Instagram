from .models import Notificacion


def notificaciones_no_leidas(request):
    """Envía a TODAS las plantillas el número de notificaciones sin leer (círculo rojo del menú)."""
    if request.user.is_authenticated:
        total = Notificacion.objects.filter(user=request.user, leida=False).count()
        return {'notificaciones_no_leidas': total}
    return {'notificaciones_no_leidas': 0}
