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
]