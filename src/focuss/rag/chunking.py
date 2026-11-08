"""Divide o texto do documento em trechos para recuperação (RAG).

Regras: o trecho não passa de `tamanho` caracteres, corta preferencialmente entre
parágrafos e depois entre frases, nunca atravessa páginas (para mostrar a página de
origem no cartão) e repete o fim do trecho anterior (`sobreposicao`) para não perder
contexto na fronteira.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from focuss.rag.extracao_pdf import Pagina

TAMANHO_PADRAO = 800
SOBREPOSICAO_PADRAO = 150

_FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+")


@dataclass(frozen=True)
class TrechoTexto:
    ordem: int
    pagina: int
    texto: str


def dividir_em_trechos(
    paginas: Iterable[Pagina],
    tamanho: int = TAMANHO_PADRAO,
    sobreposicao: int = SOBREPOSICAO_PADRAO,
) -> list[TrechoTexto]:
    if tamanho <= 0 or not 0 <= sobreposicao < tamanho:
        raise ValueError("use tamanho > 0 e 0 <= sobreposicao < tamanho")
    trechos: list[TrechoTexto] = []
    for pagina in paginas:
        for texto in _dividir_pagina(pagina.texto, tamanho, sobreposicao):
            trechos.append(TrechoTexto(ordem=len(trechos), pagina=pagina.numero, texto=texto))
    return trechos


def _dividir_pagina(texto: str, tamanho: int, sobreposicao: int) -> list[str]:
    pedacos = [p for p in _pedacos_pequenos(texto, tamanho) if p]
    trechos: list[str] = []
    atual = ""
    for pedaco in pedacos:
        candidato = f"{atual} {pedaco}".strip() if atual else pedaco
        if len(candidato) <= tamanho:
            atual = candidato
            continue
        trechos.append(atual)
        inicio = _cauda(atual, sobreposicao)
        atual = f"{inicio} {pedaco}".strip() if inicio else pedaco
        if len(atual) > tamanho:  # sobreposição + pedaço não cabem: fica só o pedaço
            atual = pedaco
    if atual:
        trechos.append(atual)
    return trechos


def _pedacos_pequenos(texto: str, tamanho: int) -> list[str]:
    """Parágrafos; se um parágrafo for grande, frases; se a frase for grande, palavras."""
    pedacos: list[str] = []
    for paragrafo in re.split(r"\n\s*\n", texto):
        paragrafo = " ".join(paragrafo.split())
        if len(paragrafo) <= tamanho:
            pedacos.append(paragrafo)
            continue
        for frase in _FIM_DE_FRASE.split(paragrafo):
            if len(frase) <= tamanho:
                pedacos.append(frase)
            else:
                pedacos.extend(_cortar_por_palavras(frase, tamanho))
    return pedacos


def _cortar_por_palavras(frase: str, tamanho: int) -> list[str]:
    partes, atual = [], ""
    for palavra in frase.split():
        if len(palavra) > tamanho:  # palavra absurda (ex.: URL gigante): corta a seco
            if atual:
                partes.append(atual)
                atual = ""
            partes.extend(palavra[i : i + tamanho] for i in range(0, len(palavra), tamanho))
            continue
        candidato = f"{atual} {palavra}".strip()
        if len(candidato) > tamanho:
            partes.append(atual)
            atual = palavra
        else:
            atual = candidato
    if atual:
        partes.append(atual)
    return partes


def _cauda(texto: str, sobreposicao: int) -> str:
    """Últimos `sobreposicao` caracteres, começando numa palavra inteira."""
    if sobreposicao == 0 or len(texto) <= sobreposicao:
        return "" if sobreposicao == 0 else texto
    cauda = texto[-sobreposicao:]
    espaco = cauda.find(" ")
    return cauda[espaco + 1 :] if espaco != -1 else cauda
