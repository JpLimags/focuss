from datetime import date

import pytest

from focuss.core.sm2 import Agendamento, Botao, calcular, converter_botao

HOJE = date(2026, 11, 2)


def test_primeira_revisao_boa_agenda_1_dia():
    r = calcular(Agendamento(), 4, HOJE)
    assert (r.repeticoes, r.intervalo_dias) == (1, 1)
    assert r.proxima_revisao == date(2026, 11, 3)


def test_segunda_revisao_agenda_6_dias():
    r = calcular(calcular(Agendamento(), 4, HOJE), 4, HOJE)
    assert r.intervalo_dias == 6


def test_terceira_revisao_multiplica_pelo_ef():
    a = Agendamento(repeticoes=2, intervalo_dias=6, fator_facilidade=2.5)
    assert calcular(a, 4, HOJE).intervalo_dias == 15


def test_erro_reinicia_para_1_dia():
    a = Agendamento(repeticoes=5, intervalo_dias=30, fator_facilidade=2.5)
    r = calcular(a, 1, HOJE)
    assert (r.repeticoes, r.intervalo_dias) == (0, 1)


def test_ef_nunca_fica_abaixo_de_1_3():
    a = Agendamento(fator_facilidade=1.3)
    for _ in range(10):
        a = calcular(a, 0, HOJE)
    assert a.fator_facilidade == 1.3


def test_nota_5_aumenta_ef_e_nota_4_mantem():
    assert calcular(Agendamento(), 5, HOJE).fator_facilidade == 2.6
    assert calcular(Agendamento(), 4, HOJE).fator_facilidade == 2.5


def test_nota_invalida():
    with pytest.raises(ValueError):
        calcular(Agendamento(), 6, HOJE)


def test_botoes():
    assert [converter_botao(b) for b in Botao] == [1, 3, 4, 5]
