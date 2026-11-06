from django.db import models
from django.contrib.auth.models import User

from django.conf import settings

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

    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='likes_publicaciones')

    def total_likes(self):
        return self.likes.count()
    
class Comentario(models.Model):
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='comentarios')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    texto = models.TextField()
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.texto[:20]}"

class Notificacion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='acciones_realizadas')
    tipo = models.CharField(max_length=20)  # Ejemplo: 'like'
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, null=True, blank=True)
    leida = models.BooleanField(default=False)
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.actor.username} interactuó con tu publicación"