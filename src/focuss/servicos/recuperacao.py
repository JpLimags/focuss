"""Indexação e recuperação de trechos por tópico (base do RF08).

O gerador de flashcards só vai receber o que `buscar` devolver: é isso que restringe
os cartões ao material do aluno.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from focuss.dados.modelos import Documento, Trecho
from focuss.rag.embeddings import Codificador
from focuss.rag.vetorial import ArmazenamentoVetorial

K_PADRAO = 5


class MotorBusca:
    def __init__(
        self, armazenamento: ArmazenamentoVetorial, fabrica_codificador: Callable[[], Codificador]
    ) -> None:
        self._armazenamento = armazenamento
        self._fabrica_codificador = fabrica_codificador
        self._codificador: Codificador | None = None

    @property
    def codificador(self) -> Codificador:
        # Carrega o modelo só na primeira vez que for preciso (leva alguns segundos).
        if self._codificador is None:
            self._codificador = self._fabrica_codificador()
        return self._codificador

    def indexar(self, documento: Documento) -> int:
        """Gera os embeddings dos trechos (já gravados, com id) e salva no índice."""
        trechos = documento.trechos
        if not trechos:
            return 0
        vetores = self.codificador.codificar([t.texto for t in trechos])
        self._armazenamento.adicionar(documento.id, [t.id for t in trechos], vetores)
        return len(trechos)

    def buscar(
        self, sessao: Session, documento: Documento, topico: str, k: int = K_PADRAO
    ) -> list[tuple[Trecho, float]]:
        topico = topico.strip()
        if not topico:
            return []
        vetor = self.codificador.codificar([topico])[0]
        achados = self._armazenamento.buscar(documento.id, vetor, k)
        if not achados:
            return []
        por_id = {
            t.id: t
            for t in sessao.scalars(
                select(Trecho).where(
                    Trecho.documento_id == documento.id,
                    Trecho.id.in_([i for i, _ in achados]),
                )
            )
        }
        return [(por_id[i], nota) for i, nota in achados if i in por_id]

    def remover(self, documento_id: int) -> None:
        self._armazenamento.remover_documento(documento_id)
