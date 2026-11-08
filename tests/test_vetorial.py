import numpy as np
import pytest

from focuss.rag.vetorial import ArmazenamentoFaiss


def _unitario(*valores):
    v = np.array(valores, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_busca_ordena_por_similaridade(tmp_path):
    a = ArmazenamentoFaiss(tmp_path)
    a.adicionar(1, [10, 20, 30], np.stack([_unitario(1, 0), _unitario(0, 1), _unitario(1, 1)]))
    achados = a.buscar(1, _unitario(1, 0.1), k=2)
    assert [i for i, _ in achados] == [10, 30]
    assert achados[0][1] > achados[1][1]


def test_indice_persiste_em_disco(tmp_path):
    ArmazenamentoFaiss(tmp_path).adicionar(1, [7], np.stack([_unitario(1, 0)]))
    assert ArmazenamentoFaiss(tmp_path).buscar(1, _unitario(1, 0), k=5)[0][0] == 7


def test_documentos_isolados_e_remocao(tmp_path):
    a = ArmazenamentoFaiss(tmp_path)
    a.adicionar(1, [1], np.stack([_unitario(1, 0)]))
    a.adicionar(2, [2], np.stack([_unitario(1, 0)]))
    assert [i for i, _ in a.buscar(2, _unitario(1, 0), k=5)] == [2]
    a.remover_documento(1)
    assert a.buscar(1, _unitario(1, 0), k=5) == []


def test_k_maior_que_o_indice_e_documento_inexistente(tmp_path):
    a = ArmazenamentoFaiss(tmp_path)
    a.adicionar(1, [1, 2], np.stack([_unitario(1, 0), _unitario(0, 1)]))
    assert len(a.buscar(1, _unitario(1, 0), k=50)) == 2
    assert a.buscar(99, _unitario(1, 0), k=5) == []


def test_tamanhos_diferentes(tmp_path):
    with pytest.raises(ValueError):
        ArmazenamentoFaiss(tmp_path).adicionar(1, [1, 2], np.stack([_unitario(1, 0)]))
