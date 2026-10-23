from getpass import getpass

import uvicorn

from main import crear_app


if __name__ == "__main__":
    clave = getpass("Contrasena de PostgreSQL: ")
    uvicorn.run(crear_app(clave), host="127.0.0.1", port=8000)
