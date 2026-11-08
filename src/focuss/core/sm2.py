"""Motor de repetição espaçada SM-2 (lógica determinística, sem LLM)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum

EF_INICIAL = 2.5
EF_MINIMO = 1.3


class Botao(Enum):
    """Botões da tela de resposta e a nota SM-2 (0 a 5) de cada um."""

    ERREI = 1
    DIFICIL = 3
    BOM = 4
    FACIL = 5


@dataclass(frozen=True)
class Agendamento:
    repeticoes: int = 0
    intervalo_dias: int = 0
    fator_facilidade: float = EF_INICIAL
    proxima_revisao: date | None = None


def calcular(agendamento: Agendamento, nota: int, hoje: date) -> Agendamento:
    """Aplica uma resposta (nota 0 a 5) e devolve o novo agendamento."""
    if not 0 <= nota <= 5:
        raise ValueError("nota deve estar entre 0 e 5")

    if nota < 3:
        repeticoes, intervalo = 0, 1
    else:
        repeticoes = agendamento.repeticoes + 1
        if agendamento.repeticoes == 0:
            intervalo = 1
        elif agendamento.repeticoes == 1:
            intervalo = 6
        else:
            intervalo = round(agendamento.intervalo_dias * agendamento.fator_facilidade)

    q = 5 - nota
    ef = agendamento.fator_facilidade + (0.1 - q * (0.08 + q * 0.02))
    ef = max(EF_MINIMO, ef)

    return replace(
        agendamento,
        repeticoes=repeticoes,
        intervalo_dias=intervalo,
        fator_facilidade=round(ef, 4),
        proxima_revisao=hoje + timedelta(days=intervalo),
    )


def converter_botao(botao: Botao) -> int:
    return botao.value
