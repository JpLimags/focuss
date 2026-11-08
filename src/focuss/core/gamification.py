"""Regras de jogo determinísticas (XP, nível, sequência). Valores a calibrar (RN12/RN13)."""

from __future__ import annotations

from datetime import date

from focuss.core.sm2 import Botao

XP_POR_BOTAO = {Botao.ERREI: 2, Botao.DIFICIL: 5, Botao.BOM: 8, Botao.FACIL: 10}
XP_BASE_NIVEL = 100  # XP para sair do nível n = XP_BASE_NIVEL * n


def xp_da_resposta(botao: Botao, revisao_agendada: bool, aprovado: bool = True) -> int:
    """XP só vale para revisão agendada de cartão aprovado (anti-farm, RF35)."""
    if not revisao_agendada or not aprovado:
        return 0
    return XP_POR_BOTAO[botao]


def xp_para_sair_do_nivel(nivel: int) -> int:
    if nivel < 1:
        raise ValueError("nivel começa em 1")
    return XP_BASE_NIVEL * nivel


def nivel_do_xp(xp_total: int) -> int:
    """Nível calculado pelo XP acumulado. Como XP nunca diminui, o nível também não."""
    if xp_total < 0:
        raise ValueError("xp_total não pode ser negativo")
    nivel, restante = 1, xp_total
    while restante >= xp_para_sair_do_nivel(nivel):
        restante -= xp_para_sair_do_nivel(nivel)
        nivel += 1
    return nivel


def atualizar_sequencia(
    sequencia: int, ultimo_dia: date | None, hoje: date, descanso_livre: bool = False
) -> int:
    """Sequência de dias. Pular um dia só mantém se houver descanso livre na semana.

    Perder a sequência nunca remove XP, nível ou conquistas (RN).
    """
    if ultimo_dia is None:
        return 1
    dias = (hoje - ultimo_dia).days
    if dias <= 0:
        return sequencia
    if dias == 1:
        return sequencia + 1
    if dias == 2 and descanso_livre:
        return sequencia + 1
    return 1
