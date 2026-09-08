from datetime import date

import pytest
from pydantic import ValidationError

from carta_bar.modelos import Persona, Reserva


def test_persona_valida() -> None:
    persona = Persona(nombre="Ana", edad=30)
    assert persona.edad == 30


def test_persona_edad_negativa() -> None:
    with pytest.raises(ValidationError):
        Persona(nombre="Ana", edad=-5)


def test_reserva_valida() -> None:
    reserva = Reserva(fecha_inicio=date(2026, 8, 1), fecha_fin=date(2026, 8, 10))
    assert reserva.fecha_inicio == date(2026, 8, 1)


def test_reserva_fechas_invertidas() -> None:
    with pytest.raises(ValidationError):
        Reserva(fecha_inicio=date(2026, 8, 10), fecha_fin=date(2026, 8, 1))


def test_persona_edad_excesiva() -> None:
    with pytest.raises(ValidationError):
        Persona(nombre="Ana", edad=200)
