"""Guardar y traducir: al crear o editar un plato desde el panel se lanza la
traduccion en segundo plano, con el tope de gasto y anotando el coste.

Sin LLM ni base de datos: se sustituyen las funciones de datos y el traductor."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth, traductor
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app
from carta_bar.costes import Consumo, ConsumoTotal
from carta_bar.modelos import Plato
from carta_bar.presupuesto import ControlGasto
from carta_bar.uso import RepositorioMemoria

CUERPO = {"nombre": "Flan", "descripcion": "Con caramelo", "precio": 4.5}


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    plato = Plato(
        id="p1", categoria="postres", nombre="Flan", descripcion="d",
        precio=4.5, ingredientes=[], alergenos=[],
    )
    monkeypatch.setattr(
        "carta_bar.api.actualizar_plato_editable", lambda rid, pid, *r, **k: pid != "no-existe"
    )
    monkeypatch.setattr(
        "carta_bar.api.crear_plato", lambda rid, cat, *r, **k: None if cat == "no-existe" else plato
    )
    monkeypatch.setattr("carta_bar.api.crear_plato_especial", lambda rid, *r, **k: plato)
    monkeypatch.setattr("carta_bar.api.actualizar_disponibilidad", lambda rid, pid, d: True)
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def test_editar_un_plato_pide_traducir(
    cliente: TestClient, traducciones_pedidas: list[str]
) -> None:
    assert cliente.put("/admin/api/platos/p1", json=CUERPO).status_code == 204
    assert traducciones_pedidas == [RESTAURANTE_ID]


def test_crear_un_plato_pide_traducir(
    cliente: TestClient, traducciones_pedidas: list[str]
) -> None:
    r = cliente.post("/admin/api/platos", json={**CUERPO, "categoria": "postres"})
    assert r.status_code == 201
    assert traducciones_pedidas == [RESTAURANTE_ID]


def test_crear_un_especial_pide_traducir(
    cliente: TestClient, traducciones_pedidas: list[str]
) -> None:
    assert cliente.post("/admin/api/platos/especiales", json=CUERPO).status_code == 201
    assert traducciones_pedidas == [RESTAURANTE_ID]


def test_si_no_se_guarda_nada_no_se_traduce(
    cliente: TestClient, traducciones_pedidas: list[str]
) -> None:
    assert cliente.put("/admin/api/platos/no-existe", json=CUERPO).status_code == 404
    r = cliente.post("/admin/api/platos", json={**CUERPO, "categoria": "no-existe"})
    assert r.status_code == 404
    assert TestClient(app).put("/admin/api/platos/p1", json=CUERPO).status_code == 401
    assert traducciones_pedidas == []


def test_agotar_un_plato_no_traduce(cliente: TestClient, traducciones_pedidas: list[str]) -> None:
    r = cliente.post("/admin/api/platos/p1/disponibilidad", json={"disponible": False})
    assert r.status_code == 204
    assert traducciones_pedidas == []


# ------------------------------------------------------- traducir_restaurante


def _gasto(coste: float) -> ConsumoTotal:
    return ConsumoTotal(consumos=[Consumo(llamada="traduccion", coste_usd=coste)])


@pytest.fixture
def control() -> ControlGasto:
    return ControlGasto(RepositorioMemoria(), tope_diario=1.0)


def test_traduce_los_tres_idiomas_y_anota_el_coste(
    monkeypatch: pytest.MonkeyPatch, control: ControlGasto
) -> None:
    idiomas: list[str] = []

    def falsa(rid: str, idioma: str) -> ConsumoTotal:
        idiomas.append(idioma)
        return _gasto(0.10)

    monkeypatch.setattr(traductor, "traducir_carta", falsa)
    traductor.traducir_restaurante("bar-1", control)
    assert idiomas == ["en", "de", "fr"]
    assert control.repositorio.gasto_del_dia("bar-1") == pytest.approx(0.30)


def test_sin_presupuesto_no_traduce(
    monkeypatch: pytest.MonkeyPatch, control: ControlGasto
) -> None:
    control.registrar("bar-1", "haiku", _gasto(1.0))
    llamadas: list[str] = []
    monkeypatch.setattr(
        traductor, "traducir_carta", lambda rid, idioma: llamadas.append(idioma) or _gasto(0.1)
    )
    traductor.traducir_restaurante("bar-1", control)
    assert llamadas == []


def test_un_idioma_que_falla_no_impide_los_demas(
    monkeypatch: pytest.MonkeyPatch, control: ControlGasto
) -> None:
    def falsa(rid: str, idioma: str) -> ConsumoTotal:
        if idioma == "de":
            raise RuntimeError("la API no responde")
        return _gasto(0.10)

    monkeypatch.setattr(traductor, "traducir_carta", falsa)
    traductor.traducir_restaurante("bar-1", control)  # no debe lanzar
    assert control.repositorio.gasto_del_dia("bar-1") == pytest.approx(0.20)


def test_sin_cambios_no_se_anota_nada(
    monkeypatch: pytest.MonkeyPatch, control: ControlGasto
) -> None:
    monkeypatch.setattr(traductor, "traducir_carta", lambda rid, idioma: ConsumoTotal())
    traductor.traducir_restaurante("bar-1", control)
    assert control.repositorio.gasto_del_dia("bar-1") == 0.0
