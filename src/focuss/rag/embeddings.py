"""Embeddings dos trechos. O modelo real é carregado só quando usado (é pesado)."""

from __future__ import annotations

from typing import Protocol

import numpy as np

# Modelo multilíngue pequeno (~470 MB), bom para português e roda em CPU.
MODELO_PADRAO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Codificador(Protocol):
    dimensao: int

    def codificar(self, textos: list[str]) -> np.ndarray:
        """Matriz float32 (len(textos) x dimensao) com vetores de norma 1."""
        ...


class CodificadorSentenceTransformers:
    def __init__(self, modelo: str = MODELO_PADRAO) -> None:
        from sentence_transformers import SentenceTransformer  # import adiado: torch é pesado

        self._modelo = SentenceTransformer(modelo)
        self.dimensao = self._modelo.get_embedding_dimension()  # nome desde a versão 6

    def codificar(self, textos: list[str]) -> np.ndarray:
        vetores = self._modelo.encode(
            textos, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
        return np.asarray(vetores, dtype=np.float32).reshape(len(textos), self.dimensao)
