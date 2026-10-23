from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15, unique=True, verbose_name="Número de teléfono")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de nacimiento")

    def __str__(self):
        return self.user.username
    
class Publicacion(models.Model):
    # Relaciona la foto con el usuario que la subió
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Campo para subir la imagen (se guardará en una carpeta llamada 'publicaciones/')
    imagen = models.ImageField(upload_to='publicaciones/')
    
    # Descripción o pie de foto opcional
    descripcion = models.TextField(blank=True, null=True)
    
    # Fecha y hora automática de cuándo se creó
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.creado_el.strftime('%d/%m/%Y')}" 