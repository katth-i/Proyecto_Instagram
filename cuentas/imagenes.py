"""
Validación y optimización de las imágenes que suben los usuarios.

- Solo acepta JPG, PNG, WEBP y GIF (lo que los navegadores muestran sin problemas).
- Rechaza archivos de más de 10 MB.
- Gira la foto según la información de la cámara (EXIF) para que no salga de lado.
- Reduce el tamaño (máx. 1440 px) y la guarda como JPG: pesa mucho menos,
  carga más rápido y no satura el servidor.
- Los GIF se dejan tal cual para no perder la animación.
"""
import os
from io import BytesIO

from django import forms
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps

FORMATOS_PERMITIDOS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
TAMANO_MAXIMO_MB = 10
MENSAJE_FORMATO = "Formato no compatible. Sube una imagen JPG, PNG, WEBP o GIF."


def procesar_imagen(archivo, max_lado=1440, calidad=85):
    # Si no se subió un archivo nuevo (ej. se mantiene la foto de perfil actual), no se toca
    if not isinstance(archivo, UploadedFile):
        return archivo

    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise forms.ValidationError(f"La imagen pesa demasiado. El máximo es {TAMANO_MAXIMO_MB} MB.")

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        formato = imagen.format
        imagen.load()
    except Exception:
        raise forms.ValidationError("No se pudo leer la imagen. Puede estar dañada o no ser una imagen. " + MENSAJE_FORMATO)

    if formato not in FORMATOS_PERMITIDOS:
        raise forms.ValidationError(f"El formato {formato or 'desconocido'} no está permitido. " + MENSAJE_FORMATO)

    if formato == 'GIF':
        archivo.seek(0)
        return archivo

    try:
        imagen = ImageOps.exif_transpose(imagen)  # corrige fotos giradas del celular
        # Las imágenes con transparencia (PNG/WEBP) se ponen sobre fondo blanco
        if imagen.mode in ('RGBA', 'LA', 'P'):
            imagen = imagen.convert('RGBA')
            fondo = Image.new('RGB', imagen.size, (255, 255, 255))
            fondo.paste(imagen, mask=imagen.split()[-1])
            imagen = fondo
        elif imagen.mode != 'RGB':
            imagen = imagen.convert('RGB')

        imagen.thumbnail((max_lado, max_lado))
        buffer = BytesIO()
        imagen.save(buffer, format='JPEG', quality=calidad, optimize=True)
    except Exception:
        raise forms.ValidationError("No se pudo procesar la imagen. Intenta con otra foto.")

    nombre = os.path.splitext(os.path.basename(archivo.name))[0][:50] or 'foto'
    return ContentFile(buffer.getvalue(), name=f"{nombre}.jpg")
