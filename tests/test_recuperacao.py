from focuss.dados.modelos import Usuario
from focuss.servicos.documentos import enviar_documento


def _documento(sessao, pdf):
    usuario = Usuario(nome="Ana", email="ana@ex.com", senha_hash="x")
    sessao.add(usuario)
    doc, _ = enviar_documento(
        sessao,
        usuario,
        "bio.pdf",
        pdf(
            "A mitocondria produz energia celular na forma de ATP.",
            "O cloroplasto realiza a fotossintese usando luz solar.",
            "O nucleo guarda o DNA da celula.",
        ),
    )
    return doc


def test_upload_grava_trechos_com_pagina(sessao, pdf):
    doc = _documento(sessao, pdf)
    assert [(t.ordem, t.pagina) for t in doc.trechos] == [(0, 1), (1, 2), (2, 3)]


def test_busca_traz_o_trecho_do_topico(sessao, pdf, motor):
    doc = _documento(sessao, pdf)
    assert motor.indexar(doc) == 3
    achados = motor.buscar(sessao, doc, "onde fica o DNA?", k=1)
    assert achados[0][0].pagina == 3


def test_topico_vazio_ou_documento_sem_indice(sessao, pdf, motor):
    doc = _documento(sessao, pdf)
    assert motor.buscar(sessao, doc, "   ") == []
    assert motor.buscar(sessao, doc, "DNA") == []  # ainda não indexado


def test_modelo_so_carrega_quando_usado(tmp_path):
    from focuss.rag.vetorial import ArmazenamentoFaiss
    from focuss.servicos.recuperacao import MotorBusca

    chamadas = []
    MotorBusca(ArmazenamentoFaiss(tmp_path), lambda: chamadas.append(1))
    assert chamadas == []
