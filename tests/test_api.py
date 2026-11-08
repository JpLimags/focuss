import pytest
from fastapi.testclient import TestClient

from focuss.api.app import criar_app

CONTA = {"nome": "Ana", "email": "ana@ex.com", "senha": "senha-forte"}
TEXTO = "Fotossintese converte luz em energia quimica nas plantas."


@pytest.fixture
def cliente(motor):
    with TestClient(criar_app("sqlite://", chave_secreta="teste", motor_busca=motor)) as c:
        yield c


@pytest.fixture
def logado(cliente):
    assert cliente.post("/api/cadastro", json=CONTA).status_code == 201
    return cliente


def test_cadastro_ja_loga(cliente):
    r = cliente.post("/api/cadastro", json=CONTA)
    assert r.status_code == 201
    assert r.json()["nivel"] == 1
    assert "senha" not in r.text
    assert cliente.get("/api/eu").json()["email"] == "ana@ex.com"


def test_cadastro_invalido_mostra_mensagem(cliente):
    r = cliente.post("/api/cadastro", json={**CONTA, "senha": "123"})
    assert r.status_code == 400
    assert "8 caracteres" in r.json()["detail"]


def test_login_logout(logado):
    logado.post("/api/logout")
    assert logado.get("/api/eu").status_code == 401
    assert (
        logado.post("/api/login", json={"email": "ana@ex.com", "senha": "errada!!"}).status_code
        == 401
    )
    r = logado.post("/api/login", json={"email": "ana@ex.com", "senha": "senha-forte"})
    assert r.status_code == 200
    assert logado.get("/api/eu").status_code == 200


def test_rotas_protegidas_sem_login(cliente):
    assert cliente.get("/api/eu").status_code == 401
    assert cliente.get("/api/documentos").status_code == 401
    r = cliente.post("/api/documentos", files={"arquivo": ("a.pdf", b"%PDF-", "application/pdf")})
    assert r.status_code == 401


def test_upload_e_listagem(logado, pdf):
    r = logado.post(
        "/api/documentos",
        files={"arquivo": ("aula1.pdf", pdf(TEXTO, ""), "application/pdf")},
    )
    assert r.status_code == 201
    assert r.json()["num_paginas"] == 2
    assert r.json()["paginas_sem_texto"] == [2]
    lista = logado.get("/api/documentos").json()
    assert [d["nome_arquivo"] for d in lista] == ["aula1.pdf"]


def test_upload_pdf_sem_texto(logado, pdf):
    r = logado.post("/api/documentos", files={"arquivo": ("scan.pdf", pdf(""), "application/pdf")})
    assert r.status_code == 422
    assert "texto selecionável" in r.json()["detail"]
    assert logado.get("/api/documentos").json() == []


def test_upload_grande_demais(logado, pdf, monkeypatch):
    from focuss.rag import extracao_pdf

    monkeypatch.setattr(extracao_pdf, "TAMANHO_MAXIMO_BYTES", 100)
    r = logado.post("/api/documentos", files={"arquivo": ("a.pdf", pdf(TEXTO), "application/pdf")})
    assert r.status_code == 422


def test_usuario_nao_ve_documento_de_outro(logado, pdf):
    logado.post("/api/documentos", files={"arquivo": ("a.pdf", pdf(TEXTO), "application/pdf")})
    logado.post("/api/logout")
    logado.post("/api/cadastro", json={**CONTA, "email": "bia@ex.com"})
    assert logado.get("/api/documentos").json() == []


def test_upload_gera_trechos_e_busca_por_topico(logado, pdf):
    r = logado.post(
        "/api/documentos",
        files={
            "arquivo": (
                "bio.pdf",
                pdf(
                    "A mitocondria produz energia celular na forma de ATP.",
                    "O cloroplasto realiza a fotossintese usando luz solar.",
                ),
                "application/pdf",
            )
        },
    )
    doc = r.json()
    assert doc["num_trechos"] == 2
    achados = logado.get(
        f"/api/documentos/{doc['id']}/busca", params={"topico": "fotossintese luz", "k": 1}
    ).json()
    assert len(achados) == 1
    assert achados[0]["pagina"] == 2
    assert "cloroplasto" in achados[0]["texto"]


def test_busca_em_documento_de_outro_usuario_da_404(logado, pdf):
    doc = logado.post(
        "/api/documentos", files={"arquivo": ("a.pdf", pdf(TEXTO), "application/pdf")}
    ).json()
    logado.post("/api/logout")
    logado.post("/api/cadastro", json={**CONTA, "email": "bia@ex.com"})
    r = logado.get(f"/api/documentos/{doc['id']}/busca", params={"topico": "luz"})
    assert r.status_code == 404
