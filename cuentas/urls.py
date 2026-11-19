from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('inicio/', views.inicio, name='inicio'),
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('crear/', views.crear_publicacion, name='crear'),
    path('like/<int:publicacion_id>/', views.dar_like, name='dar_like'),
    path('comentario/<int:publicacion_id>/', views.agregar_comentario, name='agregar_comentario'),
    path('notificaciones/', views.ver_notificaciones, name='notificaciones'),
    path('buscar/', views.buscar, name='buscar'),
    path('publicacion/<int:publicacion_id>/', views.ver_publicacion, name='publicacion'),
    path('publicacion/<int:publicacion_id>/eliminar/', views.eliminar_publicacion, name='eliminar_publicacion'),
    path('api/notificaciones/', views.estado_notificaciones, name='estado_notificaciones'),
    path('api/publicaciones/', views.estado_publicaciones, name='estado_publicaciones'),
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('perfil/<str:username>/', views.ver_perfil, name='perfil'),
    path('perfil/<str:username>/seguir/', views.seguir_usuario, name='seguir'),
    path('perfil/<str:username>/seguidores/', views.lista_seguimiento, {'tipo': 'seguidores'}, name='seguidores'),
    path('perfil/<str:username>/seguidos/', views.lista_seguimiento, {'tipo': 'seguidos'}, name='seguidos'),
]