from django.db import models
from django.contrib.auth.models import User

from django.conf import settings

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # null=True para que las cuentas creadas con createsuperuser también puedan tener perfil
    # (el formulario de registro los sigue pidiendo como obligatorios)
    telefono = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Número de teléfono")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de nacimiento")
    # Campos nuevos para la página de perfil (opcionales, para no afectar a los usuarios ya creados)
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True, verbose_name="Foto de perfil")
    bio = models.TextField(max_length=150, blank=True, verbose_name="Biografía")
    # Última vez que cambió su nombre de usuario (solo se permite cada 7 días)
    username_cambiado_el = models.DateTimeField(null=True, blank=True)

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

    # Oculta por moderación (o automáticamente al recibir varios reportes)
    oculta = models.BooleanField(default=False)

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


class Seguimiento(models.Model):
    """'seguidor' sigue a 'seguido'. Si los dos se siguen, son amigos (seguimiento mutuo)."""
    seguidor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='siguiendo')
    seguido = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seguidores')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        # No se puede seguir dos veces a la misma persona
        constraints = [models.UniqueConstraint(fields=['seguidor', 'seguido'], name='seguimiento_unico')]

    def __str__(self):
        return f"{self.seguidor.username} sigue a {self.seguido.username}"



class Guardado(models.Model):
    """Publicación que un usuario guardó (🔖). Solo la ve ese usuario."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guardados')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='guardada_por')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'publicacion'], name='guardado_unico')]

    def __str__(self):
        return f"{self.user.username} guardó la publicación {self.publicacion_id}"


class Reporte(models.Model):
    """Reporte de una publicación. Lo revisan los moderadores."""
    MOTIVOS = [
        ('spam', 'Spam o publicidad'),
        ('inapropiado', 'Desnudos o contenido inapropiado'),
        ('acoso', 'Acoso o bullying'),
        ('violencia', 'Violencia u odio'),
        ('falso', 'Información falsa'),
        ('otro', 'Otro motivo'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('resuelto', 'Resuelto (se tomó acción)'),
        ('descartado', 'Descartado (no había problema)'),
    ]
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='reportes')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reportes_hechos')
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    detalle = models.CharField(max_length=300, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Cada persona puede reportar una misma publicación una sola vez
        constraints = [models.UniqueConstraint(fields=['publicacion', 'usuario'], name='reporte_unico')]

    def __str__(self):
        return f"Reporte de {self.usuario.username} a la publicación {self.publicacion_id} ({self.get_motivo_display()})"



class MejorAmigo(models.Model):
    """'user' tiene a 'amigo' en su lista de mejores amigos ⭐ (solo 'user' ve su lista)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mejores_amigos')
    amigo = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mejor_amigo_de')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'amigo'], name='mejor_amigo_unico')]

    def __str__(self):
        return f"{self.amigo.username} es mejor amigo de {self.user.username}"


class Silenciado(models.Model):
    """'user' silenció a 'silenciado': sus publicaciones no aparecen en el feed de 'user'."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='silencios')
    silenciado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='silenciado_por')
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'silenciado'], name='silenciado_unico')]

    def __str__(self):
        return f"{self.user.username} silenció a {self.silenciado.username}"
