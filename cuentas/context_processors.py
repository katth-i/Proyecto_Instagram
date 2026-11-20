from .models import Notificacion, Reporte


def notificaciones_no_leidas(request):
    """Envía a TODAS las plantillas el número de notificaciones sin leer (círculo rojo del menú)."""
    if request.user.is_authenticated:
        total = Notificacion.objects.filter(user=request.user, leida=False).count()
        return {'notificaciones_no_leidas': total}
    return {'notificaciones_no_leidas': 0}


def reportes_pendientes(request):
    """Para los moderadores: cuántas publicaciones tienen reportes sin revisar."""
    if request.user.is_authenticated and request.user.is_staff:
        total = Reporte.objects.filter(estado='pendiente').values('publicacion').distinct().count()
        return {'reportes_pendientes': total}
    return {'reportes_pendientes': 0}
