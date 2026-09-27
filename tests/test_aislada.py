"""La suite nunca debe hablar con la base de datos real (ver tests/conftest.py).

Sin la proteccion del conftest, un PC con las credenciales de Supabase en el
.env hacia que los tests de mesas crearan mesas y sesiones en produccion."""

from carta_bar.api import _repositorio_uso, mesas, metricas, productos
from carta_bar.mesas import RepositorioMesasMemoria
from carta_bar.metricas import RepositorioMetricasMemoria
from carta_bar.productos import RepositorioProductosMemoria
from carta_bar.uso import RepositorioMemoria


def test_los_repositorios_de_la_suite_son_en_memoria() -> None:
    assert isinstance(mesas, RepositorioMesasMemoria)
    assert isinstance(_repositorio_uso, RepositorioMemoria)
    assert isinstance(metricas, RepositorioMetricasMemoria)
    assert isinstance(productos, RepositorioProductosMemoria)
