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
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('perfil/<str:username>/', views.ver_perfil, name='perfil'),
    path('perfil/<str:username>/seguir/', views.seguir_usuario, name='seguir'),
    path('perfil/<str:username>/seguidores/', views.lista_seguimiento, {'tipo': 'seguidores'}, name='seguidores'),
    path('perfil/<str:username>/seguidos/', views.lista_seguimiento, {'tipo': 'seguidos'}, name='seguidos'),
]