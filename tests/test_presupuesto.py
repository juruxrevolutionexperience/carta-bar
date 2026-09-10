"""El corte por gasto es lo que separa una noche mala de una factura mala."""

import pytest

from carta_bar.costes import Consumo, ConsumoTotal
from carta_bar.presupuesto import ControlGasto
from carta_bar.uso import RepositorioMemoria


def consumo(coste: float) -> ConsumoTotal:
    return ConsumoTotal(consumos=[Consumo(llamada="respuesta", coste_usd=coste)])


@pytest.fixture
def control() -> ControlGasto:
    return ControlGasto(RepositorioMemoria(), tope_diario=1.0)


def test_deja_gastar_mientras_quede_presupuesto(control: ControlGasto) -> None:
    control.registrar("la-catedral", "haiku", consumo(0.40))
    assert control.hay_presupuesto("la-catedral") is True


def test_corta_al_alcanzar_el_tope(control: ControlGasto) -> None:
    control.registrar("la-catedral", "haiku", consumo(1.0))
    assert control.hay_presupuesto("la-catedral") is False


def test_el_gasto_se_acumula_entre_preguntas(control: ControlGasto) -> None:
    for _ in range(4):
        control.registrar("la-catedral", "haiku", consumo(0.30))
    assert control.hay_presupuesto("la-catedral") is False


def test_el_tope_es_por_restaurante(control: ControlGasto) -> None:
    control.registrar("la-catedral", "haiku", consumo(2.0))
    assert control.hay_presupuesto("la-catedral") is False
    # Que uno se pase no puede dejar sin servicio a los demas.
    assert control.hay_presupuesto("otro-bar") is True


def test_si_la_contabilidad_falla_se_sigue_sirviendo() -> None:
    class RepositorioRoto(RepositorioMemoria):
        def gasto_del_dia(self, restaurante_id: str) -> float:
            raise ConnectionError("base de datos caida")

    # Fallo abierto deliberado: la carta no se cae por un fallo de metricas.
    assert ControlGasto(RepositorioRoto()).hay_presupuesto("la-catedral") is True


def test_un_fallo_al_anotar_no_tumba_la_respuesta() -> None:
    class RepositorioRoto(RepositorioMemoria):
        def registrar(self, restaurante_id: str, modelo: str, c: ConsumoTotal) -> None:
            raise ConnectionError("base de datos caida")

    # La respuesta ya esta pagada; perder la anotacion no debe propagarse.
    ControlGasto(RepositorioRoto()).registrar("la-catedral", "haiku", consumo(0.01))


def test_el_repositorio_guarda_una_fila_por_llamada() -> None:
    repo = RepositorioMemoria()
    total = ConsumoTotal(
        consumos=[
            Consumo(llamada="interprete", coste_usd=0.0007),
            Consumo(llamada="respuesta", coste_usd=0.0029),
        ]
    )
    repo.registrar("la-catedral", "haiku", total)
    assert len(repo.filas) == 2
    assert repo.gasto_del_dia("la-catedral") == pytest.approx(0.0036)


def test_el_aviso_no_se_repite_en_cada_peticion_bloqueada(control: ControlGasto) -> None:
    control.registrar("la-catedral", "haiku", consumo(2.0))

    # 200 peticiones bloqueadas seguidas: el corte actua siempre, el log una vez.
    for _ in range(200):
        assert control.hay_presupuesto("la-catedral") is False

    assert len(control._ultimo_aviso) == 1


def test_el_freno_de_avisos_es_por_restaurante(control: ControlGasto) -> None:
    control.registrar("bar-uno", "haiku", consumo(2.0))
    control.registrar("bar-dos", "haiku", consumo(2.0))

    control.hay_presupuesto("bar-uno")
    control.hay_presupuesto("bar-dos")

    # Que uno este silenciado no puede tapar el aviso de otro.
    assert len(control._ultimo_aviso) == 2
