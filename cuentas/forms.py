from django import forms
from django.contrib.auth.models import User
from .models import Perfil
from datetime import date

class RegistroForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")
    username = forms.CharField(max_length=30, required=True, label="Nombre de usuario")
    email = forms.EmailField(required=True, label="Correo electrónico")
    telefono = forms.CharField(max_length=15, required=True, label="Número de teléfono")
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de nacimiento")
    
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
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
            if edad > 100:
                raise forms.ValidationError("Por favor, ingresa una fecha de nacimiento válida.")
                
        return fecha

    # Validar que el nombre de usuario no exista
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso. Elige otro.")
        if len(username) > 30:
            raise forms.ValidationError("El nombre de usuario no debe superar los 30 caracteres.")
        return username

    # Validar que el correo no exista
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    # Validar que el teléfono no exista
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
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
            raise forms.ValidationError("Las contraseñas no coinciden. Por favor, verifica.")
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