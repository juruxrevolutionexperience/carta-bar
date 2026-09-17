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
