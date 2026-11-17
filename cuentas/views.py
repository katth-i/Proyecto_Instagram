from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from datetime import timedelta
from django.db.models import Count
from django.utils import timezone
from .forms import RegistroForm, PublicacionForm, UsuarioEditForm, PerfilEditForm
from .models import Publicacion, Comentario, Notificacion, Perfil, Seguimiento


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
    publicaciones = Publicacion.objects.all().order_by('-id')
    return render(request, 'cuentas/inicio.html', {'publicaciones': publicaciones})


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
        texto = request.POST.get('texto')
        if texto:
            Comentario.objects.create(
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
    return redirect('inicio')


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
            
    return redirect('inicio')


@never_cache
@login_required
def ver_notificaciones(request):
    notificaciones = Notificacion.objects.filter(user=request.user).order_by('-creado_el')
    notificaciones.update(leida=True)  # Marcar como leídas al abrirlas
    return render(request, 'cuentas/notificaciones.html', {'notificaciones': notificaciones})


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
    return redirect('perfil', username=usuario.username)


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
