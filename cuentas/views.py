from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm, PublicacionForm
from .models import Publicacion, Comentario, Notificacion, Perfil


def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Cuenta creada con éxito! Ya puedes iniciar sesión.')
            return redirect('login')
    else:
        form = RegistroForm()
    
    return render(request, 'cuentas/registro.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        identificador = request.POST.get('username')  # Puede ser usuario, email o teléfono
        password = request.POST.get('password')
        
        user = None
        # 1. Intentar buscar por username
        try:
            user_obj = User.objects.get(username=identificador)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

        # 2. Si no, intentar buscar por email
        if not user:
            try:
                user_obj = User.objects.get(email=identificador)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        # 3. Si no, intentar buscar por teléfono en el Perfil
        if not user:
            try:
                perfil_obj = Perfil.objects.get(telefono=identificador)
                user = authenticate(request, username=perfil_obj.user.username, password=password)
            except Perfil.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return redirect('inicio')
        else:
            messages.error(request, 'Credenciales incorrectas. Verifica tus datos e intenta de nuevo.')

    return render(request, 'cuentas/login.html')


@login_required
def inicio(request):
    # Obtenemos todas las publicaciones de la base de datos (ordenadas de la más nueva a la más vieja)
    publicaciones = Publicacion.objects.all().order_by('-id')
    return render(request, 'cuentas/inicio.html', {'publicaciones': publicaciones})


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


@login_required
def ver_notificaciones(request):
    notificaciones = Notificacion.objects.filter(user=request.user).order_by('-creado_el')
    notificaciones.update(leida=True)  # Marcar como leídas al abrirlas
    return render(request, 'cuentas/notificaciones.html', {'notificaciones': notificaciones})