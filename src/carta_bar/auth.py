"""Login del panel de gestion: contrasena unica por restaurante.

Todo con la libreria estandar (hashlib/hmac/secrets), sin dependencias
nuevas: pbkdf2 para el hash de la contrasena, HMAC para firmar la cookie
de sesion.
"""

import base64
import hashlib
import hmac
import os
import secrets
import time

_ITERACIONES_PBKDF2 = 600_000
_DURACION_SESION_S = 12 * 60 * 60


def hash_clave(clave: str) -> str:
    sal = secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal), _ITERACIONES_PBKDF2
    )
    return f"pbkdf2_sha256${_ITERACIONES_PBKDF2}${sal}${derivado.hex()}"


def verificar_clave(clave: str, hash_guardado: str) -> bool:
    try:
        algoritmo, iteraciones_txt, sal, hash_esperado = hash_guardado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    derivado = hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal), int(iteraciones_txt)
    )
    return hmac.compare_digest(derivado.hex(), hash_esperado)


def _secreto_sesion() -> bytes:
    secreto = os.getenv("SESION_SECRETO", "")
    if not secreto:
        secreto = secrets.token_hex(32)
        os.environ["SESION_SECRETO"] = secreto
    return secreto.encode("utf-8")


def crear_token_sesion(restaurante_id: str) -> str:
    expira_en = int(time.time()) + _DURACION_SESION_S
    carga = f"{restaurante_id}:{expira_en}"
    firma = hmac.new(_secreto_sesion(), carga.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{carga}:{firma}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")


def verificar_token_sesion(token: str) -> str | None:
    try:
        carga_completa = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        restaurante_id, expira_en_txt, firma = carga_completa.rsplit(":", 2)
    except (ValueError, UnicodeDecodeError):
        return None

    carga = f"{restaurante_id}:{expira_en_txt}"
    firma_esperada = hmac.new(_secreto_sesion(), carga.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, firma_esperada):
        return None
    if int(expira_en_txt) < int(time.time()):
        return None
    return restaurante_id
