"""Fija el restaurante resuelto por subdominio al de siempre (RESTAURANTE_ID)
para toda la suite, salvo donde un test lo pida explicitamente (ver
test_multitenant.py). Sin esto, cada peticion de TestClient (Host: testserver)
intentaria de verdad comprobar si "testserver" es un restaurante real."""

import os

# Los tests NUNCA deben tocar la base de datos real. `llm.py` carga el .env al
# importarse, y en un PC con las credenciales de Supabase eso conectaria la suite
# a produccion (los tests de mesas crean mesas y sesiones de verdad). Se vacian
# antes de importar nada de carta_bar: load_dotenv no pisa lo que ya esta puesto.
for _variable in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_HOST"):
    os.environ[_variable] = ""
os.environ["CARTA_BD_ACTIVA"] = "false"

import pytest  # noqa: E402

from carta_bar import api  # noqa: E402
from carta_bar.api import RESTAURANTE_ID, _resolver_restaurante, app  # noqa: E402

# Red de seguridad, no solo las variables de arriba: si por lo que sea
# (un .env con credenciales, un cambio futuro) algun repositorio de api.py
# terminara siendo el de Postgres en vez de memoria, mejor que la suite entera
# falle aqui mismo a que un test de verdad cree mesas o sesiones en produccion
# (como paso el 2026-10-06: "Terraza API 1..4" en la-catedral).
for _nombre_repo in ("mesas", "productos", "propuestas", "comandas", "cuentas"):
    _repo = getattr(api, _nombre_repo)
    _clase = type(_repo).__name__
    if "Postgres" in _clase:
        raise RuntimeError(
            f"carta_bar.api.{_nombre_repo} es {_clase}, no memoria: los tests no "
            "pueden correr asi (tocarian la base de datos real). Revisa que "
            "POSTGRES_USER/PASSWORD/DB/HOST esten vacios en el entorno."
        )


@pytest.fixture(autouse=True)
def _restaurante_fijo():
    app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def traducciones_pedidas(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Guardar un plato lanza la traduccion en segundo plano, y TestClient la
    ejecuta de verdad al terminar la peticion: sin esto, cada test del panel
    llamaria al LLM. Devuelve los restaurantes cuya traduccion se pidio."""
    pedidas: list[str] = []
    monkeypatch.setattr(
        "carta_bar.api.traducir_restaurante", lambda rid, control: pedidas.append(rid)
    )
    return pedidas
