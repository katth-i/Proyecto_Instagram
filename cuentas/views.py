from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm
from .models import Perfil
from .forms import PublicacionForm
from .models import Publicacion


@login_required(login_url='login')
def inicio(request):
    return render(request, 'cuentas/inicio.html')

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
def crear_publicacion(request):
    if request.method == 'POST':
        # Recibimos los datos de texto y los archivos (imágenes) que mandó el usuario
        form = PublicacionForm(request.POST, request.FILES)
        if form.is_valid():
            # commit=False nos permite detener el guardado un segundo para asignarle el usuario actual
            publicacion = form.save(commit=False)
            publicacion.user = request.user  # Asignamos la foto al usuario que ha iniciado sesión
            publicacion.save()  # Ahora sí guardamos en la base de datos
            return redirect('inicio')  # Redirigimos al muro principal
    else:
        form = PublicacionForm()
    return render(request, 'cuentas/crear.html', {'form': form})

    

def inicio(request):
    # Obtenemos todas las publicaciones de la base de datos (ordenadas de la más nueva a la más vieja)
    publicaciones = Publicacion.objects.all().order_by('-id')
    return render(request, 'cuentas/inicio.html', {'publicaciones': publicaciones})
