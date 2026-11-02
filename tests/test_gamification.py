from datetime import date

import pytest

from focuss.core.gamification import atualizar_sequencia, nivel_do_xp, xp_da_resposta
from focuss.core.sm2 import Botao


def test_xp_por_botao():
    assert [xp_da_resposta(b, True) for b in Botao] == [2, 5, 8, 10]


def test_sem_xp_fora_da_revisao_agendada_ou_rascunho():
    assert xp_da_resposta(Botao.FACIL, revisao_agendada=False) == 0
    assert xp_da_resposta(Botao.FACIL, revisao_agendada=True, aprovado=False) == 0


def test_nivel_pelo_xp_acumulado():
    assert nivel_do_xp(0) == 1
    assert nivel_do_xp(99) == 1
    assert nivel_do_xp(100) == 2
    assert nivel_do_xp(300) == 3


def test_nivel_nunca_diminui_com_mais_xp():
    niveis = [nivel_do_xp(x) for x in range(0, 2000, 7)]
    assert niveis == sorted(niveis)


def test_xp_negativo_invalido():
    with pytest.raises(ValueError):
        nivel_do_xp(-1)


def test_sequencia():
    d = date(2026, 11, 2)
    assert atualizar_sequencia(0, None, d) == 1
    assert atualizar_sequencia(3, date(2026, 11, 1), d) == 4
    assert atualizar_sequencia(3, d, d) == 3
    assert atualizar_sequencia(3, date(2026, 10, 31), d, descanso_livre=True) == 4
    assert atualizar_sequencia(3, date(2026, 10, 31), d) == 1
