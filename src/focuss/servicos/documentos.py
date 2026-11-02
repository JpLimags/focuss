"""Caso de uso: enviar um PDF (RF04-05)."""

from __future__ import annotations

from pathlib import PurePath

from sqlalchemy.orm import Session

from focuss.dados.modelos import Documento, Usuario
from focuss.rag.extracao_pdf import PdfInvalido, TextoExtraido, extrair_texto


def enviar_documento(
    sessao: Session, usuario: Usuario, nome_arquivo: str, conteudo: bytes
) -> tuple[Documento, TextoExtraido]:
    """Extrai o texto e grava o Documento. Levanta ErroPdf com mensagem para o aluno.

    Devolve também o resultado da extração, para a tela avisar páginas sem texto.
    """
    nome = _nome_seguro(nome_arquivo)
    if not nome.lower().endswith(".pdf"):
        raise PdfInvalido("Só aceitamos arquivos .pdf.")
    extraido = extrair_texto(conteudo)
    documento = Documento(
        usuario=usuario,
        nome_arquivo=nome,
        num_paginas=extraido.num_paginas,
        texto=extraido.texto_completo,
    )
    sessao.add(documento)
    sessao.flush()
    return documento, extraido


def _nome_seguro(nome_arquivo: str) -> str:
    # Navegadores podem mandar caminho completo (C:\...\aula.pdf); fica só o nome.
    nome = PurePath(nome_arquivo.replace("\\", "/")).name.strip()
    return nome[:255] or "documento.pdf"
