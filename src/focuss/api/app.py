"""API web (FastAPI). Só traduz HTTP para os casos de uso em focuss.servicos.

Rodar: uvicorn focuss.api.app:criar_app --factory --reload
"""

import os
import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from focuss.dados.banco import criar_engine, criar_tabelas, fabrica_de_sessoes
from focuss.dados.modelos import Documento, Usuario
from focuss.rag import extracao_pdf
from focuss.rag.embeddings import CodificadorSentenceTransformers
from focuss.rag.extracao_pdf import ErroPdf, PdfGrandeDemais
from focuss.rag.vetorial import ArmazenamentoFaiss
from focuss.servicos.contas import ErroCadastro, autenticar, cadastrar
from focuss.servicos.documentos import enviar_documento
from focuss.servicos.recuperacao import MotorBusca

CHAVE_SESSAO = "usuario_id"


class DadosCadastro(BaseModel):
    nome: str
    email: str
    senha: str


class DadosLogin(BaseModel):
    email: str
    senha: str


class UsuarioSaida(BaseModel):
    id: int
    nome: str
    email: str
    modo_foco: bool
    nivel: int
    xp_total: int


class DocumentoSaida(BaseModel):
    id: int
    nome_arquivo: str
    num_paginas: int
    num_trechos: int
    paginas_sem_texto: list[int] = []


class TrechoSaida(BaseModel):
    id: int
    pagina: int
    texto: str
    similaridade: float


def motor_busca_padrao() -> MotorBusca:
    pasta = os.environ.get("FOCUSS_INDICES", "data/indices")
    return MotorBusca(ArmazenamentoFaiss(pasta), CodificadorSentenceTransformers)


def criar_app(
    url_banco: str | None = None,
    chave_secreta: str | None = None,
    motor_busca: MotorBusca | None = None,
) -> FastAPI:
    motor = motor_busca or motor_busca_padrao()
    engine = criar_engine(url_banco)
    criar_tabelas(engine)
    fabrica = fabrica_de_sessoes(engine)

    app = FastAPI(title="Focuss")
    chave = chave_secreta or os.environ.get("FOCUSS_SECRET_KEY") or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=chave, same_site="lax", https_only=False)

    def sessao_banco() -> Iterator[Session]:
        with fabrica() as sessao:
            try:
                yield sessao
                sessao.commit()
            except Exception:
                sessao.rollback()
                raise

    Banco = Annotated[Session, Depends(sessao_banco)]

    def usuario_logado(request: Request, sessao: Banco) -> Usuario:
        usuario_id = request.session.get(CHAVE_SESSAO)
        usuario = sessao.get(Usuario, usuario_id) if usuario_id else None
        if usuario is None:
            request.session.clear()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
        return usuario

    Logado = Annotated[Usuario, Depends(usuario_logado)]

    @app.post("/api/cadastro", status_code=status.HTTP_201_CREATED)
    def rota_cadastro(dados: DadosCadastro, request: Request, sessao: Banco) -> UsuarioSaida:
        try:
            usuario = cadastrar(sessao, dados.nome, dados.email, dados.senha)
        except ErroCadastro as erro:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(erro)) from erro
        request.session[CHAVE_SESSAO] = usuario.id
        return _usuario_saida(usuario)

    @app.post("/api/login")
    def rota_login(dados: DadosLogin, request: Request, sessao: Banco) -> UsuarioSaida:
        usuario = autenticar(sessao, dados.email, dados.senha)
        if usuario is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
        request.session.clear()
        request.session[CHAVE_SESSAO] = usuario.id
        return _usuario_saida(usuario)

    @app.post("/api/logout", status_code=status.HTTP_204_NO_CONTENT)
    def rota_logout(request: Request) -> None:
        request.session.clear()

    @app.get("/api/eu")
    def rota_eu(usuario: Logado) -> UsuarioSaida:
        return _usuario_saida(usuario)

    @app.post("/api/documentos", status_code=status.HTTP_201_CREATED)
    async def rota_enviar_documento(
        arquivo: UploadFile, usuario: Logado, sessao: Banco
    ) -> DocumentoSaida:
        limite = extracao_pdf.TAMANHO_MAXIMO_BYTES
        conteudo = await arquivo.read(limite + 1)  # não carrega arquivos gigantes inteiros
        try:
            if len(conteudo) > limite:
                raise PdfGrandeDemais(f"O arquivo passa de {limite // (1024 * 1024)} MB.")
            documento, extraido = enviar_documento(
                sessao, usuario, arquivo.filename or "", conteudo
            )
        except ErroPdf as erro:
            raise HTTPException(422, str(erro)) from erro
        motor.indexar(documento)
        return _documento_saida(documento, extraido.paginas_sem_texto)

    @app.get("/api/documentos")
    def rota_listar_documentos(usuario: Logado, sessao: Banco) -> list[DocumentoSaida]:
        documentos = sessao.scalars(
            select(Documento)
            .where(Documento.usuario_id == usuario.id)
            .order_by(Documento.enviado_em.desc())
        )
        return [_documento_saida(d) for d in documentos]

    @app.get("/api/documentos/{documento_id}/busca")
    def rota_buscar_trechos(
        documento_id: int,
        usuario: Logado,
        sessao: Banco,
        topico: Annotated[str, Query(min_length=1, max_length=200)],
        k: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> list[TrechoSaida]:
        documento = sessao.get(Documento, documento_id)
        if documento is None or documento.usuario_id != usuario.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento não encontrado.")
        return [
            TrechoSaida(id=t.id, pagina=t.pagina, texto=t.texto, similaridade=round(nota, 4))
            for t, nota in motor.buscar(sessao, documento, topico, k)
        ]

    return app


def _documento_saida(
    documento: Documento, paginas_sem_texto: list[int] | None = None
) -> DocumentoSaida:
    return DocumentoSaida(
        id=documento.id,
        nome_arquivo=documento.nome_arquivo,
        num_paginas=documento.num_paginas,
        num_trechos=len(documento.trechos),
        paginas_sem_texto=paginas_sem_texto or [],
    )


def _usuario_saida(usuario: Usuario) -> UsuarioSaida:
    return UsuarioSaida(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        modo_foco=usuario.modo_foco,
        nivel=usuario.perfil.nivel if usuario.perfil else 1,
        xp_total=usuario.perfil.xp_total if usuario.perfil else 0,
    )
