from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone
from .forms import RegistroForm, PublicacionForm, UsuarioEditForm, PerfilEditForm
from .models import Publicacion, Comentario, Notificacion, Perfil, Seguimiento, Guardado, Reporte


def _es_ajax(request):
    """True si la petición la hizo el JavaScript de la página (fetch), no un clic normal."""
    return request.headers.get('X-Requested-With') == 'fetch'


def _comentario_json(c):
    from django.utils.timesince import timesince
    return {
        'id': c.id,
        'usuario': c.user.username,
        'texto': c.texto,
        'hace': timesince(c.creado_el).split(',')[0],
        'perfil': reverse('perfil', args=[c.user.username]),
    }


def _volver(request, por_defecto):
    """Redirige a ?next=... (si es una dirección de Fotitos) o a la página por defecto."""
    siguiente = request.POST.get('next') or request.GET.get('next')
    if siguiente and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        return redirect(siguiente)
    return redirect(por_defecto)


@never_cache
def registro_view(request):
    # Si ya inició sesión, no tiene sentido registrarse otra vez
    if request.user.is_authenticated:
        return redirect('inicio')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Cuenta creada con éxito! Ya puedes iniciar sesión.')
            return redirect('login')
    else:
        form = RegistroForm()
    
    return render(request, 'cuentas/registro.html', {'form': form})


@never_cache
def login_view(request):
    # Si ya hay una sesión abierta, no se puede entrar con otra cuenta encima:
    # primero hay que cerrar sesión (evita que se cambie de cuenta sin querer)
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        identificador = request.POST.get('username', '').strip()  # Puede ser usuario, email o teléfono
        password = request.POST.get('password')

        # Buscar la cuenta por usuario, correo o teléfono (sin importar mayúsculas)
        user_obj = (
            User.objects.filter(username__iexact=identificador).first()
            or User.objects.filter(email__iexact=identificador).first()
        )
        if user_obj is None:
            perfil_obj = Perfil.objects.filter(telefono=identificador).first()
            user_obj = perfil_obj.user if perfil_obj else None

        user = None
        if user_obj is not None:
            user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            # Si venía de una página protegida (?next=...), lo devolvemos ahí
            siguiente = request.POST.get('next') or request.GET.get('next')
            if siguiente and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
                return redirect(siguiente)
            return redirect('inicio')
        else:
            messages.error(request, 'Credenciales incorrectas. Verifica tus datos e intenta de nuevo.')

    return render(request, 'cuentas/login.html', {'next': request.GET.get('next', '')})


@never_cache
@login_required
def inicio(request):
    # Obtenemos todas las publicaciones de la base de datos (ordenadas de la más nueva a la más vieja)
    # Las publicaciones ocultas por moderación no aparecen en el feed
    publicaciones = Publicacion.objects.filter(oculta=False).order_by('-id')
    return render(request, 'cuentas/inicio.html', {
        'publicaciones': publicaciones,
        'mis_guardados': set(request.user.guardados.values_list('publicacion_id', flat=True)),
    })


@never_cache
@login_required
def crear_publicacion(request):
    if request.method == 'POST':
        form = PublicacionForm(request.POST, request.FILES)
        if form.is_valid():
            publicacion = form.save(commit=False)
            publicacion.user = request.user  # Asignamos la foto al usuario actual
            publicacion.save()  
            return redirect('inicio')  
    else:
        form = PublicacionForm()
    return render(request, 'cuentas/crear.html', {'form': form})


@never_cache
@login_required
def agregar_comentario(request, publicacion_id):
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    if request.method == 'POST':
        texto = (request.POST.get('texto') or '').strip()[:500]
        if texto:
            comentario = Comentario.objects.create(
                publicacion=publicacion,
                user=request.user,
                texto=texto
            )
            # Crear notificación si no es su propia publicación
            if request.user != publicacion.user:
                Notificacion.objects.create(
                    user=publicacion.user,
                    actor=request.user,
                    tipo='comentario',
                    publicacion=publicacion
                )
            if _es_ajax(request):
                return JsonResponse({
                    'ok': True,
                    'comentario': _comentario_json(comentario),
                    'num_comentarios': publicacion.comentarios.count(),
                })
    if _es_ajax(request):
        return JsonResponse({'ok': False, 'error': 'Escribe un comentario.'}, status=400)
    return _volver(request, reverse('inicio') + f'#pub-{publicacion.id}')


@never_cache
@login_required
def dar_like(request, publicacion_id):
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    
    if request.user in publicacion.likes.all():
        publicacion.likes.remove(request.user)
        # Si quita el like, eliminamos la notificación correspondiente
        Notificacion.objects.filter(user=publicacion.user, actor=request.user, publicacion=publicacion, tipo='like').delete()
    else:
        publicacion.likes.add(request.user)
        # Si le da like y no es su propia publicación, creamos la notificación
        if request.user != publicacion.user:
            Notificacion.objects.create(
                user=publicacion.user,
                actor=request.user,
                tipo='like',
                publicacion=publicacion
            )

    if _es_ajax(request):
        return JsonResponse({
            'likes': publicacion.likes.count(),
            'le_di_like': publicacion.likes.filter(pk=request.user.pk).exists(),
        })
    return _volver(request, reverse('inicio') + f'#pub-{publicacion.id}')


@never_cache
@login_required
def ver_notificaciones(request):
    notificaciones = list(
        Notificacion.objects.filter(user=request.user)
        .select_related('actor', 'actor__perfil', 'publicacion')
        .order_by('-creado_el')[:100]
    )
    Notificacion.objects.filter(user=request.user, leida=False).update(leida=True)  # marcar como leídas
    return render(request, 'cuentas/notificaciones.html', {
        'notificaciones': notificaciones,
        # para saber a quién ya sigo (y mostrar "Seguir también" o "Siguiendo")
        'mis_seguidos': set(request.user.siguiendo.values_list('seguido_id', flat=True)),
    })


@never_cache
@login_required
def ver_perfil(request, username):
    # Busca al usuario por su nombre; si no existe muestra error 404
    usuario = get_object_or_404(User, username=username)
    perfil = Perfil.objects.filter(user=usuario).first()  # puede ser None (ej. el superusuario)

    # Publicaciones del usuario con sus contadores (para mostrarlos al pasar el mouse)
    publicaciones = (
        Publicacion.objects.filter(user=usuario)
        .annotate(num_likes=Count('likes', distinct=True),
                  num_comentarios=Count('comentarios', distinct=True))
        .order_by('-creado_el')
    )
    # Las publicaciones ocultas por moderación solo las ve su autor
    if request.user != usuario:
        publicaciones = publicaciones.filter(oculta=False)

    contexto = {
        'usuario_perfil': usuario,
        'perfil': perfil,
        'publicaciones': publicaciones,
        'es_mi_perfil': request.user == usuario,
        'num_seguidores': usuario.seguidores.count(),
        'num_seguidos': usuario.siguiendo.count(),
        # ¿Yo lo sigo? ¿Él me sigue? (si ambos: son amigos)
        'lo_sigo': Seguimiento.objects.filter(seguidor=request.user, seguido=usuario).exists(),
        'me_sigue': Seguimiento.objects.filter(seguidor=usuario, seguido=request.user).exists(),
    }
    return render(request, 'cuentas/perfil.html', contexto)


@never_cache
@login_required
def editar_perfil(request):
    # Si la cuenta no tiene perfil (ej. creada con createsuperuser), se le crea uno vacío
    perfil, _ = Perfil.objects.get_or_create(user=request.user)

    # Desde cuándo puede volver a cambiar su nombre de usuario (None = ya puede)
    DIAS_ENTRE_CAMBIOS = 7
    proximo_cambio = None
    if perfil.username_cambiado_el:
        fecha_permitida = perfil.username_cambiado_el + timedelta(days=DIAS_ENTRE_CAMBIOS)
        if timezone.now() < fecha_permitida:
            proximo_cambio = fecha_permitida

    # Se edita una copia del usuario para que, si hay errores, el menú no muestre un alias sin guardar
    usuario = User.objects.get(pk=request.user.pk)

    if request.method == 'POST':
        form_usuario = UsuarioEditForm(request.POST, instance=usuario)
        form_perfil = PerfilEditForm(request.POST, request.FILES, instance=perfil)
        if form_usuario.is_valid() and form_perfil.is_valid():
            cambio_alias = usuario.username != request.user.username
            if cambio_alias and proximo_cambio:
                form_usuario.add_error(
                    'username',
                    f"Solo puedes cambiar tu nombre de usuario cada {DIAS_ENTRE_CAMBIOS} días. "
                    f"Podrás hacerlo de nuevo el {timezone.localtime(proximo_cambio).strftime('%d/%m/%Y a las %H:%M')}."
                )
            else:
                form_usuario.save()
                if cambio_alias:
                    perfil.username_cambiado_el = timezone.now()
                form_perfil.save()  # guarda también username_cambiado_el
                messages.success(request, '¡Perfil actualizado!')
                return redirect('perfil', username=usuario.username)
    else:
        form_usuario = UsuarioEditForm(instance=usuario)
        form_perfil = PerfilEditForm(instance=perfil)

    return render(request, 'cuentas/editar_perfil.html', {
        'form_usuario': form_usuario,
        'form_perfil': form_perfil,
        'perfil': perfil,
        'proximo_cambio': proximo_cambio,
    })

@never_cache
@login_required
def seguir_usuario(request, username):
    """Seguir / dejar de seguir (funciona como el botón de like)."""
    usuario = get_object_or_404(User, username=username)
    if request.method == 'POST' and usuario != request.user:
        seguimiento = Seguimiento.objects.filter(seguidor=request.user, seguido=usuario)
        if seguimiento.exists():
            seguimiento.delete()
            Notificacion.objects.filter(user=usuario, actor=request.user, tipo='seguir').delete()
        else:
            Seguimiento.objects.create(seguidor=request.user, seguido=usuario)
            Notificacion.objects.create(user=usuario, actor=request.user, tipo='seguir')
    # Volver a la página desde donde se pulsó el botón (búsqueda, lista de seguidores...)
    siguiente = request.POST.get('next')
    if siguiente and url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        return redirect(siguiente)
    return redirect('perfil', username=usuario.username)


@never_cache
@login_required
def buscar(request):
    """Buscar usuarios por nombre de usuario, nombre o apellido."""
    consulta = request.GET.get('q', '').strip().lstrip('@')
    if consulta:
        personas = User.objects.filter(
            Q(username__icontains=consulta) | Q(first_name__icontains=consulta) | Q(last_name__icontains=consulta)
        ).exclude(pk=request.user.pk)
        # Primero los que empiezan con lo escrito
        personas = sorted(personas.select_related('perfil')[:50],
                          key=lambda u: (not u.username.lower().startswith(consulta.lower()), u.username.lower()))
        sugerencias = False
    else:
        # Sin búsqueda: sugerir gente que todavía no sigo
        personas = (User.objects.exclude(pk=request.user.pk)
                    .exclude(seguidores__seguidor=request.user)
                    .select_related('perfil')
                    .annotate(total_seguidores=Count('seguidores'))
                    .order_by('-total_seguidores', '-date_joined')[:15])
        sugerencias = True
    mis_seguidos = set(request.user.siguiendo.values_list('seguido_id', flat=True))
    me_siguen = set(request.user.seguidores.values_list('seguidor_id', flat=True))
    return render(request, 'cuentas/buscar.html', {
        'consulta': consulta,
        'personas': personas,
        'sugerencias': sugerencias,
        'mis_seguidos': mis_seguidos,
        'me_siguen': me_siguen,
    })


@never_cache
@login_required
def lista_seguimiento(request, username, tipo):
    """Lista de seguidores o de seguidos de un usuario."""
    usuario = get_object_or_404(User, username=username)
    if tipo == 'seguidores':
        personas = User.objects.filter(siguiendo__seguido=usuario)
        titulo = 'Seguidores'
    else:
        personas = User.objects.filter(seguidores__seguidor=usuario)
        titulo = 'Seguidos'
    personas = personas.select_related('perfil').order_by('username')
    mis_seguidos = set(request.user.siguiendo.values_list('seguido_id', flat=True))
    return render(request, 'cuentas/lista_seguimiento.html', {
        'usuario_perfil': usuario,
        'personas': personas,
        'titulo': titulo,
        'mis_seguidos': mis_seguidos,
    })


@never_cache
@login_required
def ver_publicacion(request, publicacion_id):
    """Página de una publicación: foto, likes y todos sus comentarios."""
    publicacion = get_object_or_404(
        Publicacion.objects.select_related('user', 'user__perfil'), id=publicacion_id
    )
    if publicacion.oculta and publicacion.user != request.user and not request.user.is_staff:
        messages.error(request, 'Esta publicación no está disponible.')
        return redirect('inicio')
    comentarios = publicacion.comentarios.select_related('user', 'user__perfil').order_by('creado_el')
    return render(request, 'cuentas/publicacion.html', {
        'publicacion': publicacion,
        'comentarios': comentarios,
        'le_di_like': publicacion.likes.filter(pk=request.user.pk).exists(),
        'es_mia': publicacion.user == request.user,
        'mis_guardados': set(request.user.guardados.filter(publicacion=publicacion).values_list('publicacion_id', flat=True)),
        'ya_reporte': publicacion.reportes.filter(usuario=request.user).exists(),
    })


@login_required
@require_POST
def eliminar_publicacion(request, publicacion_id):
    """Solo el dueño puede eliminar su publicación."""
    publicacion = get_object_or_404(Publicacion, id=publicacion_id, user=request.user)
    publicacion.imagen.delete(save=False)  # borra también el archivo (local o Cloudinary)
    publicacion.delete()
    messages.success(request, 'Publicación eliminada.')
    return redirect('perfil', username=request.user.username)


@login_required
def estado_notificaciones(request):
    """
    La consulta el navegador cada pocos segundos (sin recargar la página).
    Devuelve cuántas notificaciones sin leer hay y las nuevas desde la última revisada.
    """
    no_leidas = Notificacion.objects.filter(user=request.user, leida=False)
    try:
        desde = int(request.GET.get('desde', 0))
    except ValueError:
        desde = 0
    textos = {
        'like': 'le dio me gusta a tu publicación ❤️',
        'comentario': 'comentó en tu publicación 💬',
        'seguir': 'comenzó a seguirte 👤',
    }
    nuevas = []
    if desde:  # la primera vez solo se toma el último id, sin mostrar avisos viejos
        for n in no_leidas.filter(id__gt=desde).select_related('actor', 'actor__perfil').order_by('id')[:5]:
            perfil = getattr(n.actor, 'perfil', None)
            if n.publicacion_id:
                enlace = reverse('publicacion', args=[n.publicacion_id])
            else:
                enlace = reverse('perfil', args=[n.actor.username])
            nuevas.append({
                'id': n.id,
                'tipo': n.tipo,
                'actor': n.actor.username,
                'texto': textos.get(n.tipo, 'interactuó contigo'),
                'foto': perfil.foto.url if perfil and perfil.foto else '',
                'enlace': enlace,
            })
    ultimo = Notificacion.objects.filter(user=request.user).order_by('-id').values_list('id', flat=True).first() or 0
    # Cuántas sin leer hay de cada tipo (para la burbuja ❤️ 2  👤 1  💬 3)
    por_tipo = {'like': 0, 'comentario': 0, 'seguir': 0}
    for fila in no_leidas.values('tipo').annotate(total=Count('id')):
        por_tipo[fila['tipo']] = fila['total']
    return JsonResponse({'no_leidas': no_leidas.count(), 'por_tipo': por_tipo, 'nuevas': nuevas, 'ultimo_id': ultimo})


@login_required
def estado_publicaciones(request):
    """
    El navegador la consulta cada pocos segundos con los ids de las publicaciones que
    tiene en pantalla, y recibe likes y comentarios actualizados (sin recargar).
    """
    try:
        ids = [int(x) for x in request.GET.get('ids', '').split(',') if x][:30]
    except ValueError:
        return JsonResponse({'publicaciones': {}})
    datos = {}
    publicaciones = Publicacion.objects.filter(id__in=ids).annotate(
        num_likes=Count('likes', distinct=True), num_comentarios=Count('comentarios', distinct=True)
    )
    mis_likes = set(request.user.likes_publicaciones.filter(id__in=ids).values_list('id', flat=True))
    for p in publicaciones:
        ultimos = list(p.comentarios.select_related('user').order_by('-creado_el')[:50])[::-1]
        datos[p.id] = {
            'likes': p.num_likes,
            'le_di_like': p.id in mis_likes,
            'num_comentarios': p.num_comentarios,
            'comentarios': [_comentario_json(c) for c in ultimos],
        }
    return JsonResponse({'publicaciones': datos})


# ======================= GUARDAR PUBLICACIONES =======================

@login_required
@require_POST
def guardar_publicacion(request, publicacion_id):
    """Guardar / quitar de guardados (🔖). Responde JSON si lo pide el JavaScript."""
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    guardado = Guardado.objects.filter(user=request.user, publicacion=publicacion)
    if guardado.exists():
        guardado.delete()
        esta_guardada = False
    else:
        Guardado.objects.create(user=request.user, publicacion=publicacion)
        esta_guardada = True
    if _es_ajax(request):
        return JsonResponse({'guardada': esta_guardada})
    return _volver(request, reverse('inicio') + f'#pub-{publicacion.id}')


@never_cache
@login_required
def ver_guardados(request):
    """Colección privada de publicaciones guardadas."""
    guardados = (Guardado.objects.filter(user=request.user, publicacion__oculta=False)
                 .select_related('publicacion')
                 .annotate(num_likes=Count('publicacion__likes', distinct=True),
                           num_comentarios=Count('publicacion__comentarios', distinct=True))
                 .order_by('-creado_el'))
    return render(request, 'cuentas/guardados.html', {'guardados': guardados})


# ======================= REPORTAR PUBLICACIONES =======================

REPORTES_PARA_OCULTAR = 3   # con 3 reportes de personas distintas se oculta sola


@login_required
@require_POST
def reportar_publicacion(request, publicacion_id):
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    motivo = request.POST.get('motivo', '')
    motivos_validos = dict(Reporte.MOTIVOS)

    if publicacion.user == request.user:
        respuesta, estado = {'ok': False, 'mensaje': 'No puedes reportar tu propia publicación.'}, 400
    elif motivo not in motivos_validos:
        respuesta, estado = {'ok': False, 'mensaje': 'Elige un motivo.'}, 400
    elif Reporte.objects.filter(publicacion=publicacion, usuario=request.user).exists():
        respuesta, estado = {'ok': True, 'mensaje': 'Ya habías reportado esta publicación. Los moderadores la revisarán.'}, 200
    else:
        Reporte.objects.create(
            publicacion=publicacion, usuario=request.user, motivo=motivo,
            detalle=(request.POST.get('detalle') or '').strip()[:300],
        )
        pendientes = publicacion.reportes.filter(estado='pendiente').count()
        if pendientes >= REPORTES_PARA_OCULTAR and not publicacion.oculta:
            publicacion.oculta = True
            publicacion.save(update_fields=['oculta'])
        respuesta, estado = {'ok': True, 'mensaje': 'Gracias por avisarnos. Los moderadores revisarán la publicación.'}, 200

    if _es_ajax(request):
        return JsonResponse(respuesta, status=estado)
    (messages.success if respuesta['ok'] else messages.error)(request, respuesta['mensaje'])
    return _volver(request, reverse('inicio'))


# ======================= MODERACIÓN (solo moderadores) =======================

def _solo_moderadores(vista):
    def envoltura(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Solo los moderadores pueden entrar a esa página.')
            return redirect('inicio')
        return vista(request, *args, **kwargs)
    return envoltura


@never_cache
@login_required
@_solo_moderadores
def moderacion(request):
    """Publicaciones con reportes pendientes, la más reportada primero."""
    publicaciones = (Publicacion.objects.filter(reportes__estado='pendiente')
                     .select_related('user')
                     .annotate(num_reportes=Count('reportes', filter=Q(reportes__estado='pendiente'), distinct=True))
                     .order_by('-num_reportes', '-id').distinct())
    casos = []
    for p in publicaciones:
        reportes = p.reportes.filter(estado='pendiente').select_related('usuario').order_by('creado_el')
        motivos = {}
        for r in reportes:
            motivos[r.get_motivo_display()] = motivos.get(r.get_motivo_display(), 0) + 1
        casos.append({'publicacion': p, 'reportes': reportes, 'motivos': motivos})
    return render(request, 'cuentas/moderacion.html', {'casos': casos})


@login_required
@require_POST
@_solo_moderadores
def moderar_publicacion(request, publicacion_id):
    publicacion = get_object_or_404(Publicacion, id=publicacion_id)
    accion = request.POST.get('accion')
    pendientes = publicacion.reportes.filter(estado='pendiente')
    if accion == 'eliminar':
        publicacion.imagen.delete(save=False)
        publicacion.delete()   # sus reportes se borran con ella
        messages.success(request, 'Publicación eliminada.')
    elif accion == 'ocultar':
        publicacion.oculta = True
        publicacion.save(update_fields=['oculta'])
        pendientes.update(estado='resuelto')
        messages.success(request, 'Publicación ocultada. Solo su autor y los moderadores pueden verla.')
    elif accion == 'descartar':
        publicacion.oculta = False   # si se había ocultado sola, vuelve a mostrarse
        publicacion.save(update_fields=['oculta'])
        pendientes.update(estado='descartado')
        messages.success(request, 'Reportes descartados. La publicación sigue visible.')
    return redirect('moderacion')
