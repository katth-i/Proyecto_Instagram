from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    # Redirige la raíz '/' directamente a la página de login de cuentas
    path('', lambda request: redirect('login', permanent=False)),
    path('', include('cuentas.urls')),
]