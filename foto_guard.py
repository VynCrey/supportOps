"""Acepta solo fotos pequeñas y elimina metadatos antes de guardarlas."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 8_000_000


def preparar_foto(contenido: bytes) -> tuple[str, bytes]:
    if not contenido or len(contenido) > MAX_BYTES:
        raise ValueError("La foto debe ocupar como máximo 2 MB")
    try:
        with Image.open(BytesIO(contenido)) as imagen:
            if imagen.format not in ("JPEG", "PNG"):
                raise ValueError("Solo se aceptan fotos JPG o PNG")
            if imagen.width * imagen.height > MAX_PIXELS:
                raise ValueError("La foto tiene demasiados píxeles")
            imagen.load()
            limpia = imagen.convert("RGB")
            salida = BytesIO()
            limpia.save(salida, format="JPEG", quality=82, optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("No se pudo leer la foto") from error
    if salida.tell() > MAX_BYTES:
        raise ValueError("La foto procesada supera 2 MB")
    return "image/jpeg", salida.getvalue()
