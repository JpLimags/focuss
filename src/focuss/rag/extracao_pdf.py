"""Extração de texto de PDF (RF04-05). Sem OCR: PDF escaneado é recusado com mensagem clara."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError, PyPdfError

TAMANHO_MAXIMO_BYTES = 20 * 1024 * 1024
MINIMO_CARACTERES = 20  # abaixo disso o PDF é tratado como "sem texto selecionável"


class ErroPdf(Exception):
    """Erro com mensagem pronta para mostrar ao aluno."""


class PdfInvalido(ErroPdf):
    pass


class PdfGrandeDemais(ErroPdf):
    pass


class PdfSemTexto(ErroPdf):
    pass


@dataclass(frozen=True)
class Pagina:
    numero: int  # começa em 1, como o aluno vê no leitor
    texto: str


@dataclass(frozen=True)
class TextoExtraido:
    paginas: tuple[Pagina, ...]

    @property
    def num_paginas(self) -> int:
        return len(self.paginas)

    @property
    def texto_completo(self) -> str:
        return "\n\n".join(p.texto for p in self.paginas if p.texto)

    @property
    def paginas_sem_texto(self) -> list[int]:
        """Páginas vazias ou escaneadas, para avisar o aluno sem bloquear o envio."""
        return [p.numero for p in self.paginas if not p.texto]


def extrair_texto(conteudo: bytes) -> TextoExtraido:
    _validar_bytes(conteudo)
    leitor = _abrir(conteudo)
    paginas = tuple(
        Pagina(numero=i, texto=_limpar(_texto_da_pagina(pagina)))
        for i, pagina in enumerate(leitor.pages, start=1)
    )
    if not paginas:
        raise PdfInvalido("O PDF não tem páginas.")
    if _contar_caracteres(paginas) < MINIMO_CARACTERES:
        raise PdfSemTexto(
            "Não encontramos texto selecionável neste PDF. Ele parece ser uma imagem "
            "ou digitalização. Envie uma versão em que dê para selecionar o texto."
        )
    return TextoExtraido(paginas)


def _validar_bytes(conteudo: bytes) -> None:
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        limite_mb = TAMANHO_MAXIMO_BYTES // (1024 * 1024)
        raise PdfGrandeDemais(f"O arquivo passa de {limite_mb} MB. Envie um PDF menor.")
    if not conteudo.lstrip()[:5] == b"%PDF-":
        raise PdfInvalido("O arquivo enviado não é um PDF.")


def _abrir(conteudo: bytes) -> PdfReader:
    try:
        leitor = PdfReader(io.BytesIO(conteudo))
        if leitor.is_encrypted and not leitor.decrypt(""):
            raise PdfInvalido("O PDF está protegido por senha. Remova a senha e envie de novo.")
        return leitor
    except PdfReadError as erro:
        raise PdfInvalido("Não foi possível ler o PDF. O arquivo pode estar corrompido.") from erro


def _texto_da_pagina(pagina) -> str:
    try:
        return pagina.extract_text() or ""
    # Erros que o pypdf costuma lançar em páginas malformadas; a página é tratada como vazia.
    except (PyPdfError, KeyError, ValueError, TypeError, AttributeError):
        return ""


def _limpar(texto: str) -> str:
    texto = texto.replace("\x00", "")
    texto = re.sub(r"-\n(?=[a-zà-ú])", "", texto)  # junta palavra hifenizada na quebra
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return "\n".join(linha.strip() for linha in texto.splitlines()).strip()


def _contar_caracteres(paginas: tuple[Pagina, ...]) -> int:
    return sum(len(re.sub(r"\s", "", p.texto)) for p in paginas)
