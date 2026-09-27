"""Resolver el restaurante por subdominio: sin esto, un solo servidor no
puede atender a mas de un restaurante a la vez.

Estos tests NO usan el fixture autouse de conftest.py (que fija el
restaurante resuelto a RESTAURANTE_ID para el resto de la suite) - quitan
esa sobreescritura para ejercitar de verdad `_resolver_restaurante`.
"""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, _indice_de, _resolver_restaurante, app


@pytest.fixture
def sin_restaurante_fijo():
    """Quita la sobreescritura de conftest.py para este test en concreto."""
    app.dependency_overrides.pop(_resolver_restaurante, None)
    yield
    # El fixture autouse de conftest.py la vuelve a poner en el siguiente test.


def test_un_subdominio_conocido_resuelve_a_su_restaurante(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.api.cargar_config", lambda rid: {"nombre": rid})
    monkeypatch.setattr(
        "carta_bar.api.cargar_carta_traducida", lambda rid, idioma: [{"restaurante": rid}]
    )
    r = TestClient(app).get("/carta", headers={"Host": "bar2.jurux.app"})
    assert r.status_code == 200
    assert r.json() == [{"restaurante": "bar2", "formatos": []}]


def test_el_alias_historico_de_cartia_resuelve_a_la_catedral(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # cargar_config decide si el restaurante "existe" (dentro de la
    # resolucion); cargar_categorias es lo que de verdad pide la ruta, y aqui
    # se usa solo para comprobar con que restaurante_id se acabo llamando.
    monkeypatch.setattr("carta_bar.api.cargar_config", lambda rid: {})
    vistos: list[str] = []
    monkeypatch.setattr("carta_bar.api.cargar_categorias", lambda rid: vistos.append(rid) or [])
    TestClient(app).get("/categorias", headers={"Host": "cartia.jurux.app"})
    assert vistos == ["la-catedral"]


def test_un_subdominio_que_no_existe_da_404(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Con el DNS en comodin, un subdominio inventado llega igual al
    # servidor: antes caia al restaurante fijo y enseñaba la carta de otro
    # cliente. Ahora debe dar 404, nunca la carta de La CatedRal.
    def _cargar_config(rid: str) -> dict[str, object]:
        if rid == RESTAURANTE_ID:
            return {}
        raise ValueError("no existe")

    monkeypatch.setattr("carta_bar.api.cargar_config", _cargar_config)
    vistos: list[str] = []
    monkeypatch.setattr("carta_bar.api.cargar_categorias", lambda rid: vistos.append(rid) or [])
    r = TestClient(app).get("/categorias", headers={"Host": "no-existe.jurux.app"})
    assert r.status_code == 404
    assert vistos == []


def test_desarrollo_local_cae_al_restaurante_fijo(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch
) -> None:
    # localhost esta en la lista explicita de hosts de desarrollo: a
    # diferencia de un subdominio inventado, aqui SI debe caer al
    # restaurante fijo (no tiene sentido pedirle que sea un restaurante real).
    monkeypatch.setattr("carta_bar.api.cargar_config", lambda rid: {})
    vistos: list[str] = []
    monkeypatch.setattr("carta_bar.api.cargar_categorias", lambda rid: vistos.append(rid) or [])
    r = TestClient(app).get("/categorias", headers={"Host": "localhost:8000"})
    assert r.status_code == 200
    assert vistos == [RESTAURANTE_ID]


def test_una_sesion_de_un_restaurante_no_sirve_en_otro(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.api.cargar_config", lambda rid: {})
    cliente = TestClient(app)
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion("bar2"))

    r = cliente.get("/admin", headers={"Host": "la-catedral.jurux.app"}, follow_redirects=False)
    assert r.status_code == 303


def test_una_sesion_de_un_restaurante_si_sirve_en_el_mismo(
    sin_restaurante_fijo, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    (tmp_path / "admin.html").write_text("<h1>Panel</h1>", encoding="utf-8")
    monkeypatch.setattr("carta_bar.api.DIR_FRONTEND", tmp_path)
    monkeypatch.setattr("carta_bar.api.cargar_config", lambda rid: {})
    cliente = TestClient(app)
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion("bar2"))

    r = cliente.get("/admin", headers={"Host": "bar2.jurux.app"}, follow_redirects=False)
    assert r.status_code == 200


def test_el_indice_de_busqueda_no_mezcla_restaurantes(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[str] = []

    def _indexar_falso(modelo: object, restaurante_id: str) -> tuple[list[str], str]:
        llamadas.append(restaurante_id)
        return ([f"plato-de-{restaurante_id}"], f"vectores-de-{restaurante_id}")

    monkeypatch.setattr("carta_bar.api.indexar", _indexar_falso)
    monkeypatch.setattr("carta_bar.api._indices", {})

    carta_a, _ = _indice_de("bar2")
    carta_b, _ = _indice_de("la-catedral")
    assert carta_a == ["plato-de-bar2"]
    assert carta_b == ["plato-de-la-catedral"]

    # Volver a pedir el mismo restaurante no reindexa: usa la cache.
    _indice_de("bar2")
    assert llamadas == ["bar2", "la-catedral"]
