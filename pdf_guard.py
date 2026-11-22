"""Extrae texto de PDF pequeños sin ejecutar ni confiar en su contenido."""

from io import BytesIO


MAX_BYTES = 2 * 1024 * 1024
MAX_PAGES = 5
MAX_TEXT = 2500


def extraer_pdf(contenido: bytes) -> str:
    if not contenido.startswith(b"%PDF-"):
        raise ValueError("El archivo no es un PDF válido")
    if len(contenido) > MAX_BYTES:
        raise ValueError("El PDF supera el límite de 2 MB")
    try:
        from pypdf import PdfReader

        lector = PdfReader(BytesIO(contenido), strict=True)
        if lector.is_encrypted:
            raise ValueError("No se aceptan PDF cifrados")
        if not 1 <= len(lector.pages) <= MAX_PAGES:
            raise ValueError("El PDF debe tener entre 1 y 5 páginas")
        texto = "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("No se pudo leer el PDF") from error
    texto = " ".join(texto.split())[:MAX_TEXT]
    if not texto:
        raise ValueError("El PDF no tiene texto extraíble")
    return texto
