"""Caso de uso: enviar um PDF (RF04-05) e dividir em trechos."""

from __future__ import annotations

from pathlib import PurePath

from sqlalchemy.orm import Session

from focuss.dados.modelos import Documento, Trecho, Usuario
from focuss.rag.chunking import dividir_em_trechos
from focuss.rag.extracao_pdf import PdfInvalido, TextoExtraido, extrair_texto


def enviar_documento(
    sessao: Session, usuario: Usuario, nome_arquivo: str, conteudo: bytes
) -> tuple[Documento, TextoExtraido]:
    """Extrai o texto, grava o Documento e seus Trechos. Levanta ErroPdf com mensagem
    para o aluno. A indexação vetorial fica no MotorBusca (servicos.recuperacao).

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
        trechos=[
            Trecho(ordem=t.ordem, pagina=t.pagina, texto=t.texto)
            for t in dividir_em_trechos(extraido.paginas)
        ],
    )
    sessao.add(documento)
    sessao.flush()
    return documento, extraido


def _nome_seguro(nome_arquivo: str) -> str:
    # Navegadores podem mandar caminho completo (C:\...\aula.pdf); fica só o nome.
    nome = PurePath(nome_arquivo.replace("\\", "/")).name.strip()
    return nome[:255] or "documento.pdf"
