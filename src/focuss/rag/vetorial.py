"""Armazenamento vetorial (FAISS). Um índice por documento, salvo em disco.

Vetores normalizados + produto interno = similaridade de cosseno.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import faiss
import numpy as np


class ArmazenamentoVetorial(Protocol):
    def adicionar(self, documento_id: int, ids: list[int], vetores: np.ndarray) -> None: ...

    def buscar(self, documento_id: int, vetor: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Até k pares (id do trecho, similaridade), do mais parecido para o menos."""
        ...

    def remover_documento(self, documento_id: int) -> None: ...


class ArmazenamentoFaiss:
    def __init__(self, pasta: str | Path) -> None:
        self._pasta = Path(pasta)
        self._pasta.mkdir(parents=True, exist_ok=True)

    def adicionar(self, documento_id: int, ids: list[int], vetores: np.ndarray) -> None:
        if len(ids) != len(vetores):
            raise ValueError("ids e vetores com tamanhos diferentes")
        if not ids:
            return
        vetores = np.ascontiguousarray(vetores, dtype=np.float32)
        indice = self._carregar(documento_id) or faiss.IndexIDMap(
            faiss.IndexFlatIP(vetores.shape[1])
        )
        indice.add_with_ids(vetores, np.asarray(ids, dtype=np.int64))
        faiss.write_index(indice, str(self._arquivo(documento_id)))

    def buscar(self, documento_id: int, vetor: np.ndarray, k: int) -> list[tuple[int, float]]:
        indice = self._carregar(documento_id)
        if indice is None or indice.ntotal == 0 or k <= 0:
            return []
        consulta = np.ascontiguousarray(vetor, dtype=np.float32).reshape(1, -1)
        notas, ids = indice.search(consulta, min(k, indice.ntotal))
        return [(int(i), float(n)) for i, n in zip(ids[0], notas[0], strict=True) if i != -1]

    def remover_documento(self, documento_id: int) -> None:
        self._arquivo(documento_id).unlink(missing_ok=True)

    def _arquivo(self, documento_id: int) -> Path:
        return self._pasta / f"documento_{documento_id}.faiss"

    def _carregar(self, documento_id: int):
        arquivo = self._arquivo(documento_id)
        return faiss.read_index(str(arquivo)) if arquivo.exists() else None
