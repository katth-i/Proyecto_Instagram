from django.contrib import admin
from .models import Perfil, Publicacion, Comentario, Notificacion, Seguimiento

# Así puedes ver y editar todo desde /admin/
admin.site.register(Perfil)
admin.site.register(Publicacion)
admin.site.register(Comentario)
admin.site.register(Notificacion)
admin.site.register(Seguimiento)
