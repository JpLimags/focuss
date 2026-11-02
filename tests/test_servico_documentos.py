import pytest

from focuss.dados.modelos import Documento, Usuario
from focuss.rag.extracao_pdf import PdfInvalido, PdfSemTexto
from focuss.servicos.documentos import enviar_documento

TEXTO = "Fotossintese converte luz em energia quimica nas plantas."


@pytest.fixture
def usuario(sessao):
    u = Usuario(nome="Ana", email="ana@ex.com", senha_hash="x")
    sessao.add(u)
    sessao.flush()
    return u


def test_envio_grava_documento(sessao, usuario, pdf):
    doc, extraido = enviar_documento(sessao, usuario, "aula1.pdf", pdf(TEXTO))
    sessao.commit()
    assert doc.id is not None
    assert doc.num_paginas == 1
    assert "Fotossintese" in doc.texto
    assert extraido.paginas_sem_texto == []
    assert sessao.get(Documento, doc.id).usuario is usuario


def test_nome_vindo_com_caminho_fica_so_o_arquivo(sessao, usuario, pdf):
    doc, _ = enviar_documento(sessao, usuario, r"C:\Users\ana\Desktop\aula1.PDF", pdf(TEXTO))
    assert doc.nome_arquivo == "aula1.PDF"


def test_recusa_extensao_errada(sessao, usuario, pdf):
    with pytest.raises(PdfInvalido, match=".pdf"):
        enviar_documento(sessao, usuario, "aula1.docx", pdf(TEXTO))


def test_pdf_sem_texto_nao_grava_nada(sessao, usuario, pdf):
    with pytest.raises(PdfSemTexto):
        enviar_documento(sessao, usuario, "scan.pdf", pdf(""))
    assert sessao.query(Documento).count() == 0
