import re
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from .models import Perfil
from datetime import date
from .imagenes import procesar_imagen, MENSAJE_FORMATO
from .models import Publicacion

class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")
    username = forms.CharField(max_length=30, required=True, label="Nombre de usuario")
    email = forms.EmailField(required=True, label="Correo electrónico",
                             widget=forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.com'}))
    telefono = forms.CharField(max_length=10, required=True, label="Número de teléfono",
                               widget=forms.TextInput(attrs={
                                   'placeholder': '09XXXXXXXX', 'inputmode': 'numeric',
                                   'maxlength': '10', 'pattern': '09[0-9]{8}',
                                   'title': 'Debe tener 10 dígitos y empezar con 09',
                               }))
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de nacimiento")
    
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña",
                                help_text="Mínimo 8 caracteres, con al menos una letra y un número.")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            hoy = date.today()
            edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            
            if fecha > hoy:
                raise forms.ValidationError("La fecha de nacimiento no puede ser en el futuro.")
            if edad < 14:
                raise forms.ValidationError("Debes tener al menos 14 años para registrarte en Fotitos.")
            if edad > 100:
                raise forms.ValidationError("Por favor, ingresa una fecha de nacimiento válida.")
                
        return fecha

    # Validar que el nombre de usuario no exista
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        # Solo letras, números, punto y guion bajo (como en Instagram)
        if not re.fullmatch(r'[A-Za-z0-9._]+', username):
            raise forms.ValidationError("El nombre de usuario solo puede tener letras, números, puntos y guiones bajos (sin espacios).")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso. Elige otro.")
        if len(username) > 30:
            raise forms.ValidationError("El nombre de usuario no debe superar los 30 caracteres.")
        return username

    # Validar que el correo no exista
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        # Formato estricto: usuario@dominio.extension (ej. .com, .ec, .edu.ec)
        if not re.fullmatch(r'[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}', email):
            raise forms.ValidationError("Ingresa un correo electrónico válido (ejemplo: nombre@gmail.com).")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    # Validar que el teléfono no exista
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip().replace(' ', '')
        
        # Verificar que solo contenga números
        if not telefono.isdigit():
            raise forms.ValidationError("El número de teléfono solo debe contener dígitos numéricos.")
        
        # Verificar que tenga exactamente 10 dígitos
        if len(telefono) != 10:
            raise forms.ValidationError("El número de teléfono debe tener exactamente 10 dígitos.")
        
        # Verificar que comience con '09' (Ecuador)
        if not telefono.startswith('09'):
            raise forms.ValidationError("El número de teléfono debe comenzar con '09'.")
        
        # Verificar que no esté registrado previamente
        if Perfil.objects.filter(telefono=telefono).exists():
            raise forms.ValidationError("Este número de teléfono ya está registrado en otra cuenta.")
            
        return telefono

    # Validar que las contraseñas coincidan
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden. Por favor, verifica.")
        elif p1:
            # 1) Reglas de Django: mínimo 8 caracteres, no muy común, no solo números,
            #    no parecida al usuario/correo (ver AUTH_PASSWORD_VALIDATORS en settings.py)
            usuario_temporal = User(
                username=cleaned_data.get('username', ''),
                email=cleaned_data.get('email', ''),
                first_name=cleaned_data.get('first_name', ''),
                last_name=cleaned_data.get('last_name', ''),
            )
            try:
                password_validation.validate_password(p1, usuario_temporal)
            except forms.ValidationError as error:
                self.add_error('password1', error)
            # 2) Regla extra: al menos una letra y un número
            if not (re.search(r'[A-Za-z]', p1) and re.search(r'[0-9]', p1)):
                self.add_error('password1', "La contraseña debe tener al menos una letra y un número.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            Perfil.objects.create(
                user=user,
                telefono=self.cleaned_data["telefono"],
                fecha_nacimiento=self.cleaned_data["fecha_nacimiento"]
            )
        return user

class PublicacionForm(forms.ModelForm):
    class Meta:
        model = Publicacion
        fields = ['imagen', 'descripcion']  # Los dos campos que el usuario va a rellenar
        error_messages = {
            'imagen': {'invalid_image': MENSAJE_FORMATO, 'required': 'Selecciona una foto para publicar.'},
        }

    def clean_imagen(self):
        return procesar_imagen(self.cleaned_data.get('imagen'))


# ---------- Editar perfil ----------
class UsuarioEditForm(forms.ModelForm):
    """Alias (nombre de usuario) que se puede cambiar, como en Instagram.
    El nombre y apellido del registro NO se pueden cambiar."""
    username = forms.CharField(max_length=30, label="Nombre de usuario")

    class Meta:
        model = User
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.fullmatch(r'[A-Za-z0-9._]+', username):
            raise forms.ValidationError("Solo puede tener letras, números, puntos y guiones bajos (sin espacios).")
        # Que no lo use otra persona (sin contarse a sí mismo)
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso. Elige otro.")
        return username


class PerfilEditForm(forms.ModelForm):
    """Datos que viven en nuestro modelo Perfil."""
    class Meta:
        model = Perfil
        fields = ['foto', 'bio']
        error_messages = {'foto': {'invalid_image': MENSAJE_FORMATO}}
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'maxlength': 150, 'placeholder': 'Cuéntale algo a la gente sobre ti...'}),
        }

    def clean_foto(self):
        # Foto de perfil: más pequeña (se muestra en círculo)
        return procesar_imagen(self.cleaned_data.get('foto'), max_lado=600)
