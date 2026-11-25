"""Arma una copia portable desde los archivos versionados, sin datos locales."""

from hashlib import sha256
from pathlib import Path
import os
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile


RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ.parent / "SupportOps_netbook.zip"
EXCLUIR = {
    "docs/entrega_final/SupportOps_Informe_Proyecto_Integrador_2026.pdf",
    "docs/entrega_final/generar_informe.py",
    "docs/entrega_final/logo_instituto.png",
}
REQUERIDOS = {
    "01_PREPARAR_NETBOOK.cmd", "02_INICIAR_API.cmd",
    "03_ABRIR_PANEL.cmd", "04_ABRIR_CLIENTE.cmd",
    "05_COMPROBAR_DEMO.cmd", "verificar_netbook.py",
    "catalogo_demo.json", "kb.json", "requirements.txt", "schema.sql",
    "cliente_app.py", "streamlit_app.py", "pdf_guard.py",
    "docs/entrega_final/SupportOps_Informe_Tecnico_2026.pdf",
}


def archivos_del_paquete() -> list[str]:
    resultado = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=RAIZ
    ).decode("utf-8")
    rutas = set(resultado.strip("\0").split("\0"))
    rutas.add("crear_paquete_netbook.py")
    faltantes = REQUERIDOS - rutas
    if faltantes:
        raise RuntimeError(f"Faltan archivos de la entrega: {sorted(faltantes)}")
    return sorted(ruta for ruta in rutas if ruta and ruta not in EXCLUIR)


def main() -> None:
    temporal = SALIDA.with_suffix(".zip.tmp")
    rutas = archivos_del_paquete()
    with ZipFile(temporal, "w", compression=ZIP_DEFLATED, compresslevel=7) as paquete:
        for ruta in rutas:
            archivo = RAIZ / ruta
            if not archivo.is_file() or not archivo.resolve().is_relative_to(RAIZ):
                raise RuntimeError(f"Archivo fuera de la carpeta del proyecto: {ruta}")
            paquete.write(archivo, arcname=ruta)
    with ZipFile(temporal) as paquete:
        roto = paquete.testzip()
        if roto:
            raise RuntimeError(f"El ZIP no se pudo verificar: {roto}")
    os.replace(temporal, SALIDA)
    digest = sha256(SALIDA.read_bytes()).hexdigest()
    print(f"Paquete listo: {SALIDA}")
    print(f"Archivos: {len(rutas)} | Tamaño: {SALIDA.stat().st_size:,} bytes")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
