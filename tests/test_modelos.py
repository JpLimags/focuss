from datetime import date

from sqlalchemy import func, select

from focuss.core import sm2
from focuss.core.sm2 import Botao
from focuss.dados.modelos import (
    Agendamento,
    Documento,
    Flashcard,
    PerfilJogador,
    RespostaCartao,
    StatusCartao,
    Trecho,
    Usuario,
)

HOJE = date(2026, 11, 2)


def _montar(sessao):
    usuario = Usuario(nome="Ana", email="ana@ex.com", senha_hash="x")
    usuario.perfil = PerfilJogador()
    doc = Documento(usuario=usuario, nome_arquivo="aula.pdf", num_paginas=1, texto="t")
    trecho = Trecho(documento=doc, ordem=0, pagina=1, texto="t")
    cartao = Flashcard(documento=doc, trecho=trecho, pergunta="P?", resposta="R")
    sessao.add(usuario)
    sessao.commit()
    return usuario, cartao


def test_cartao_nasce_rascunho_sem_agendamento(sessao):
    _, cartao = _montar(sessao)
    assert cartao.status is StatusCartao.RASCUNHO
    assert cartao.agendamento is None


def test_aprovar_cria_agendamento_para_hoje(sessao):
    _, cartao = _montar(sessao)
    cartao.aprovar(HOJE)
    sessao.commit()
    assert cartao.aprovado
    assert cartao.agendamento.proxima_revisao == HOJE
    assert cartao.agendamento.fator_facilidade == sm2.EF_INICIAL


def test_aprovar_duas_vezes_nao_reinicia_agendamento(sessao):
    _, cartao = _montar(sessao)
    cartao.aprovar(HOJE)
    cartao.agendamento.repeticoes = 3
    cartao.aprovar(date(2026, 12, 1))
    assert cartao.agendamento.repeticoes == 3


def test_agendamento_ida_e_volta_com_sm2(sessao):
    _, cartao = _montar(sessao)
    cartao.aprovar(HOJE)
    novo = sm2.calcular(cartao.agendamento.para_dominio(), Botao.BOM.value, HOJE)
    cartao.agendamento.aplicar(novo)
    sessao.commit()
    sessao.expire_all()
    assert cartao.agendamento.para_dominio() == novo


def test_nivel_derivado_do_xp(sessao):
    usuario, _ = _montar(sessao)
    usuario.perfil.xp_total = 300
    assert usuario.perfil.nivel == 3


def test_excluir_usuario_apaga_tudo(sessao):
    usuario, cartao = _montar(sessao)
    cartao.aprovar(HOJE)
    cartao.respostas.append(RespostaCartao(botao=Botao.BOM, revisao_agendada=True, xp_ganho=8))
    sessao.commit()

    sessao.delete(usuario)
    sessao.commit()

    for modelo in (
        Usuario,
        PerfilJogador,
        Documento,
        Trecho,
        Flashcard,
        Agendamento,
        RespostaCartao,
    ):
        assert sessao.scalar(select(func.count()).select_from(modelo)) == 0, modelo.__name__
