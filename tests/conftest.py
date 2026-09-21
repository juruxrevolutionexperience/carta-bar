"""Fija el restaurante resuelto por subdominio al de siempre (RESTAURANTE_ID)
para toda la suite, salvo donde un test lo pida explicitamente (ver
test_multitenant.py). Sin esto, cada peticion de TestClient (Host: testserver)
intentaria de verdad comprobar si "testserver" es un restaurante real."""

import pytest

from carta_bar.api import RESTAURANTE_ID, _resolver_restaurante, app


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
