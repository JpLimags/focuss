import pytest

from focuss.rag import extracao_pdf
from focuss.rag.extracao_pdf import (
    PdfGrandeDemais,
    PdfInvalido,
    PdfSemTexto,
    extrair_texto,
)

TEXTO = "A mitocondria produz ATP pela respiracao celular."


def test_extrai_texto_por_pagina(pdf):
    r = extrair_texto(pdf(TEXTO, "Segunda pagina com conteudo."))
    assert r.num_paginas == 2
    assert r.paginas[0].numero == 1
    assert "mitocondria" in r.paginas[0].texto
    assert "Segunda pagina" in r.texto_completo


def test_mantem_acentos(pdf):
    r = extrair_texto(pdf("Revisão espaçada ajuda na memorização de conteúdo."))
    assert "Revisão espaçada" in r.texto_completo


def test_pdf_sem_texto_selecionavel(pdf):
    with pytest.raises(PdfSemTexto, match="texto selecionável"):
        extrair_texto(pdf("", ""))


def test_pagina_vazia_no_meio_e_apenas_sinalizada(pdf):
    r = extrair_texto(pdf(TEXTO, "", TEXTO))
    assert r.paginas_sem_texto == [2]


def test_arquivo_que_nao_e_pdf():
    with pytest.raises(PdfInvalido, match="não é um PDF"):
        extrair_texto(b"isto e um txt")


def test_pdf_corrompido():
    with pytest.raises(PdfInvalido):
        extrair_texto(b"%PDF-1.4\nlixo sem estrutura")


def test_arquivo_grande_demais(monkeypatch, pdf):
    monkeypatch.setattr(extracao_pdf, "TAMANHO_MAXIMO_BYTES", 100)
    with pytest.raises(PdfGrandeDemais):
        extrair_texto(pdf(TEXTO))


def test_pdf_com_senha(pdf):
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    escritor = PdfWriter(clone_from=PdfReader(BytesIO(pdf(TEXTO))))
    escritor.encrypt("segredo")
    saida = BytesIO()
    escritor.write(saida)
    with pytest.raises(PdfInvalido, match="senha"):
        extrair_texto(saida.getvalue())
