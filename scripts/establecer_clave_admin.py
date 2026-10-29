"""Establece o cambia la contrasena de acceso al panel de un restaurante.

Uso de un solo golpe, pero se puede volver a ejecutar cuando haga falta
(sobrescribe la contrasena anterior). Pide la contrasena con getpass para
que no quede en el historial de la terminal.

Uso:
    python scripts/establecer_clave_admin.py [restaurante_id]

Si no se pasa restaurante_id, usa RESTAURANTE_ID del entorno o "barX".
"""

import getpass
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from carta_bar.auth import hash_clave  # noqa: E402
from carta_bar.datos import guardar_clave_hash  # noqa: E402


def main(restaurante_id: str) -> None:
    clave = getpass.getpass(f"Nueva contraseña para '{restaurante_id}': ")
    if len(clave) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        sys.exit(1)
    confirmacion = getpass.getpass("Repite la contraseña: ")
    if clave != confirmacion:
        print("Las contraseñas no coinciden.")
        sys.exit(1)

    guardar_clave_hash(restaurante_id, hash_clave(clave))
    print(f"Contraseña actualizada para '{restaurante_id}'.")


if __name__ == "__main__":
    _por_defecto = os.getenv("RESTAURANTE_ID")
    _restaurante_id = sys.argv[1] if len(sys.argv) > 1 else _por_defecto
    if not _restaurante_id:
        print("Indica el restaurante: python scripts/establecer_clave_admin.py <restaurante_id>")
        sys.exit(1)
    main(_restaurante_id)
