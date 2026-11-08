import pytest

from focuss.rag.chunking import dividir_em_trechos
from focuss.rag.extracao_pdf import Pagina

FRASE = "A revisao espacada distribui o estudo ao longo do tempo. "


def test_pagina_curta_vira_um_trecho():
    t = dividir_em_trechos([Pagina(1, "Texto curto.")])
    assert [(x.ordem, x.pagina, x.texto) for x in t] == [(0, 1, "Texto curto.")]


def test_nenhum_trecho_passa_do_tamanho():
    texto = FRASE * 60
    trechos = dividir_em_trechos([Pagina(1, texto)], tamanho=300, sobreposicao=50)
    assert len(trechos) > 1
    assert all(len(t.texto) <= 300 for t in trechos)


def test_corta_entre_frases_e_nao_no_meio_da_palavra():
    trechos = dividir_em_trechos([Pagina(1, FRASE * 30)], tamanho=200, sobreposicao=0)
    for t in trechos:
        assert t.texto.endswith("tempo.")


def test_sobreposicao_repete_o_fim_do_trecho_anterior():
    trechos = dividir_em_trechos([Pagina(1, FRASE * 30)], tamanho=200, sobreposicao=60)
    for anterior, seguinte in zip(trechos, trechos[1:], strict=False):
        palavras_finais = anterior.texto.split()[-3:]
        assert " ".join(palavras_finais) in seguinte.texto


def test_trecho_nao_atravessa_paginas_e_guarda_a_pagina():
    trechos = dividir_em_trechos([Pagina(1, "Pagina um."), Pagina(2, ""), Pagina(3, "Tres.")])
    assert [(t.ordem, t.pagina) for t in trechos] == [(0, 1), (1, 3)]


def test_paragrafos_sao_respeitados():
    texto = "Primeiro paragrafo curto.\n\nSegundo paragrafo curto."
    trechos = dividir_em_trechos([Pagina(1, texto)], tamanho=30, sobreposicao=0)
    assert [t.texto for t in trechos] == ["Primeiro paragrafo curto.", "Segundo paragrafo curto."]


def test_frase_gigante_e_palavra_gigante():
    texto = ("palavra " * 100) + "x" * 250
    trechos = dividir_em_trechos([Pagina(1, texto)], tamanho=100, sobreposicao=20)
    assert all(len(t.texto) <= 100 for t in trechos)
    assert "".join(t.texto for t in trechos).count("x") >= 250


@pytest.mark.parametrize(("tamanho", "sobreposicao"), [(0, 0), (100, 100), (100, -1)])
def test_parametros_invalidos(tamanho, sobreposicao):
    with pytest.raises(ValueError):
        dividir_em_trechos([Pagina(1, "x")], tamanho=tamanho, sobreposicao=sobreposicao)
