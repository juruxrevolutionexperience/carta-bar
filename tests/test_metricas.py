"""Metricas de uso: visitas, preguntas al chat, conversaciones y coste.

Sin base de datos: se usa el repositorio en memoria. El SQL de Postgres solo se
valida con el parser (ver test_sql.py); lo demas, al desplegar."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import (
    COOKIE_SESION,
    COOKIE_SESION_SUPERADMIN,
    RESTAURANTE_ID,
    TOKEN_SUPERADMIN,
    app,
)
from carta_bar.costes import Consumo, ConsumoTotal
from carta_bar.limites import limiter
from carta_bar.metricas import RepositorioMetricasMemoria, es_robot
from carta_bar.modelos import ResumenRestaurante
from carta_bar.presupuesto import ControlGasto
from carta_bar.uso import RepositorioMemoria

MOVIL = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 Safari/604.1"
)
ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "Chrome/126.0 Mobile Safari/537.36"
)


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> RepositorioMetricasMemoria:
    repo = RepositorioMetricasMemoria()
    monkeypatch.setattr("carta_bar.api.metricas", repo)
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr("carta_bar.api.DIR_FRONTEND", tmp_path)
    monkeypatch.setattr("carta_bar.api._restaurante_existe", lambda rid: rid == RESTAURANTE_ID)
    limiter.reset()
    return repo


# --------------------------------------------------------------- robots


@pytest.mark.parametrize("ua", [MOVIL, ANDROID])
def test_un_movil_de_verdad_no_es_un_robot(ua: str) -> None:
    assert es_robot(ua) is False


@pytest.mark.parametrize(
    "ua",
    [
        None,
        "",
        "WhatsApp/2.23.20 A",
        "TelegramBot (like TwitterBot)",
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "facebookexternalhit/1.1",
        "curl/8.4.0",
        "python-requests/2.32",
        "Slackbot-LinkExpanding 1.0",
    ],
)
def test_reconoce_robots_y_vistas_previas(ua: str | None) -> None:
    assert es_robot(ua) is True


# --------------------------------------------------------------- visitas


def test_una_visita_de_un_cliente_se_cuenta(repo: RepositorioMetricasMemoria) -> None:
    r = TestClient(app).get("/", headers={"User-Agent": MOVIL})
    assert r.status_code == 200
    assert repo.visitas[RESTAURANTE_ID] == 1


def test_un_robot_no_cuenta(repo: RepositorioMetricasMemoria) -> None:
    TestClient(app).get("/", headers={"User-Agent": "WhatsApp/2.23"})
    assert repo.visitas[RESTAURANTE_ID] == 0


def test_el_gerente_con_sesion_abierta_no_cuenta(repo: RepositorioMetricasMemoria) -> None:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    c.get("/", headers={"User-Agent": MOVIL})
    assert repo.visitas[RESTAURANTE_ID] == 0


def test_desde_una_direccion_que_no_es_un_bar_la_pagina_se_sirve_igual(
    repo: RepositorioMetricasMemoria,
) -> None:
    # Sigue como antes: sin bar no hay visita que contar, pero tampoco 404.
    r = TestClient(app).get("/", headers={"User-Agent": MOVIL, "Host": "jurux.app"})
    assert r.status_code == 200
    assert sum(repo.visitas.values()) == 0


def test_si_falla_el_registro_la_carta_se_sirve(
    repo: RepositorioMetricasMemoria, monkeypatch: pytest.MonkeyPatch
) -> None:
    def roto(rid: str) -> None:
        raise RuntimeError("la base de datos no responde")

    monkeypatch.setattr(repo, "registrar_visita", roto)
    assert TestClient(app).get("/", headers={"User-Agent": MOVIL}).status_code == 200


# --------------------------------------------------------------- preguntas


@pytest.fixture
def chat(monkeypatch: pytest.MonkeyPatch, repo: RepositorioMetricasMemoria) -> ControlGasto:
    control = ControlGasto(RepositorioMemoria(), tope_diario=1.0)
    monkeypatch.setattr("carta_bar.api.control", control)
    monkeypatch.setattr("carta_bar.api._indice_de", lambda rid: ([], None))
    monkeypatch.setattr(
        "carta_bar.api.responder_cliente",
        lambda *a, **k: SimpleNamespace(texto="Claro", consumo=ConsumoTotal()),
    )
    return control


def preguntar(idioma: str = "es", historial: list[dict[str, str]] | None = None) -> None:
    cuerpo = {"texto": "¿Hay algo sin gluten?", "idioma": idioma, "historial": historial or []}
    r = TestClient(app).post("/preguntar", json=cuerpo)
    assert r.status_code == 200


def test_una_pregunta_sin_historial_abre_una_conversacion(
    chat: ControlGasto, repo: RepositorioMetricasMemoria
) -> None:
    preguntar("en")
    assert repo.preguntas[(RESTAURANTE_ID, "en")] == [1, 1, 0]


def test_una_pregunta_con_historial_no_abre_otra(
    chat: ControlGasto, repo: RepositorioMetricasMemoria
) -> None:
    preguntar("es")
    preguntar("es", historial=[{"rol": "cliente", "texto": "hola"}])
    assert repo.preguntas[(RESTAURANTE_ID, "es")] == [2, 1, 0]


def test_las_preguntas_se_separan_por_idioma(
    chat: ControlGasto, repo: RepositorioMetricasMemoria
) -> None:
    preguntar("es")
    preguntar("de")
    preguntar("de")
    filas = {m.restaurante_id: m for m in repo.resumen(7)}
    assert filas[RESTAURANTE_ID].preguntas_por_idioma == {"es": 1, "de": 2}


def test_sin_presupuesto_cuenta_como_rechazada_y_no_como_pregunta(
    chat: ControlGasto, repo: RepositorioMetricasMemoria
) -> None:
    agotado = ConsumoTotal(consumos=[Consumo(llamada="respuesta", coste_usd=1.0)])
    chat.registrar(RESTAURANTE_ID, "haiku", agotado)
    preguntar("fr")
    assert repo.preguntas[(RESTAURANTE_ID, "fr")] == [0, 0, 1]


# --------------------------------------------------------------- superadmin


@pytest.fixture
def superadmin(repo: RepositorioMetricasMemoria, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "carta_bar.api.listar_restaurantes",
        lambda: [
            ResumenRestaurante(id=RESTAURANTE_ID, nombre="La CatedRal", num_platos=28),
            ResumenRestaurante(id="bar-nuevo", nombre="Bar Nuevo", num_platos=0),
        ],
    )
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION_SUPERADMIN, auth.crear_token_sesion(TOKEN_SUPERADMIN))
    return c


def test_las_metricas_exigen_sesion_de_superadmin(repo: RepositorioMetricasMemoria) -> None:
    assert TestClient(app).get("/superadmin/api/metricas").status_code == 401


def test_el_gerente_no_ve_las_metricas(repo: RepositorioMetricasMemoria) -> None:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    assert c.get("/superadmin/api/metricas").status_code == 401


def test_incluye_todos_los_bares_aunque_no_tengan_actividad(
    superadmin: TestClient, repo: RepositorioMetricasMemoria
) -> None:
    repo.registrar_visita(RESTAURANTE_ID)
    datos = {f["restaurante_id"]: f for f in superadmin.get("/superadmin/api/metricas").json()}
    assert set(datos) == {RESTAURANTE_ID, "bar-nuevo"}
    assert datos[RESTAURANTE_ID]["nombre"] == "La CatedRal"
    assert datos[RESTAURANTE_ID]["visitas"] == 1
    assert datos["bar-nuevo"]["visitas"] == 0
    assert datos["bar-nuevo"]["coste_por_pregunta_usd"] is None


def test_el_periodo_se_valida(superadmin: TestClient) -> None:
    assert superadmin.get("/superadmin/api/metricas?dias=0").status_code == 422
    assert superadmin.get("/superadmin/api/metricas?dias=365").status_code == 422
    assert superadmin.get("/superadmin/api/metricas?dias=30").status_code == 200


def test_el_coste_por_pregunta_es_el_coste_del_chat_entre_preguntas() -> None:
    from carta_bar.metricas import MetricasRestaurante

    m = MetricasRestaurante(restaurante_id="x", preguntas=4, coste_chat_usd=0.02)
    assert m.coste_por_pregunta_usd == pytest.approx(0.005)
    assert m.model_dump()["coste_por_pregunta_usd"] == pytest.approx(0.005)


def test_si_las_metricas_fallan_se_avisa_sin_romper(
    superadmin: TestClient, repo: RepositorioMetricasMemoria, monkeypatch: pytest.MonkeyPatch
) -> None:
    def roto(dias: int) -> None:
        raise RuntimeError("sin base de datos")

    monkeypatch.setattr(repo, "resumen", roto)
    assert superadmin.get("/superadmin/api/metricas").status_code == 503
