import os


DB_NAME = os.getenv("SUPPORTOPS_DB_NAME", "supportops_final")
DB_HOST = os.getenv("SUPPORTOPS_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SUPPORTOPS_DB_PORT", "5432"))
DB_USER = os.getenv("SUPPORTOPS_DB_USER", "postgres")
MODEL = os.getenv("SUPPORTOPS_MODEL", "qwen2.5:3b")
OLLAMA = os.getenv("SUPPORTOPS_OLLAMA", "http://127.0.0.1:11434")

CATEGORIES = (
    "acceso",
    "facturacion",
    "api",
    "exportacion",
    "notificaciones",
    "seguridad",
)
