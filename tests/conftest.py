import pytest

from focuss.dados.banco import criar_engine, criar_tabelas, fabrica_de_sessoes


@pytest.fixture
def sessao():
    engine = criar_engine("sqlite:///:memory:")
    criar_tabelas(engine)
    with fabrica_de_sessoes(engine)() as s:
        yield s
    engine.dispose()


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def gerar_pdf(*paginas: str) -> bytes:
    """PDF mínimo válido, uma linha de texto por página (string vazia = página sem texto)."""
    n = len(paginas)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, texto in enumerate(paginas):
        fluxo = f"BT /F1 12 Tf 72 720 Td ({_escapar(texto)}) Tj ET".encode("cp1252")
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n" % len(fluxo) + fluxo + b"\nendstream")
    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for numero, objeto in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += f"{numero} 0 obj\n".encode() + objeto + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for pos in posicoes:
        saida += f"{pos:010d} 00000 n \n".encode()
    saida += (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n"
    ).encode()
    return bytes(saida)


@pytest.fixture
def pdf():
    return gerar_pdf


class CodificadorPalavras:
    """Embedding falso e determinístico para testes: saco de palavras com hash.

    Textos que dividem palavras ficam parecidos, sem precisar baixar o modelo real.
    """

    dimensao = 256

    def codificar(self, textos):
        import zlib

        import numpy as np

        matriz = np.zeros((len(textos), self.dimensao), dtype=np.float32)
        for linha, texto in enumerate(textos):
            for palavra in texto.lower().split():
                palavra = palavra.strip(".,;:!?()")
                if len(palavra) > 2:
                    matriz[linha, zlib.crc32(palavra.encode()) % self.dimensao] += 1
            norma = np.linalg.norm(matriz[linha])
            if norma:
                matriz[linha] /= norma
        return matriz


@pytest.fixture
def motor(tmp_path):
    from focuss.rag.vetorial import ArmazenamentoFaiss
    from focuss.servicos.recuperacao import MotorBusca

    return MotorBusca(ArmazenamentoFaiss(tmp_path / "indices"), CodificadorPalavras)
