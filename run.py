import os
from getpass import getpass

import uvicorn

from bootstrap import aplicar_esquema
from db import SupportOpsDB
from main import crear_app


if __name__ == "__main__":
    clave = getpass("Contrasena de PostgreSQL: ")
    # retrieval.py tambien lee PostgreSQL y psycopg toma la clave de PGPASSWORD.
    # Vive solo en este proceso: no se escribe en ningun archivo.
    os.environ["PGPASSWORD"] = clave
    with SupportOpsDB(clave).conectar() as conexion, conexion.cursor() as cursor:
        aplicar_esquema(cursor)
    uvicorn.run(crear_app(clave), host="127.0.0.1", port=8000)
