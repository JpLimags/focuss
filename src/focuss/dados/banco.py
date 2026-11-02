"""Conexão com o banco. SQLite no desenvolvimento; a URL pode vir de FOCUSS_DB_URL."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

URL_PADRAO = "sqlite:///data/focuss.db"


class Base(DeclarativeBase):
    pass


def criar_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("FOCUSS_DB_URL", URL_PADRAO)
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        os.makedirs(os.path.dirname(url.removeprefix("sqlite:///")) or ".", exist_ok=True)
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _ativar_chaves_estrangeiras)
    return engine


def _ativar_chaves_estrangeiras(conexao, _registro) -> None:
    # Sem isto o SQLite ignora ON DELETE CASCADE (necessário para excluir conta, RF03).
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def criar_tabelas(engine: Engine) -> None:
    from focuss.dados import modelos  # noqa: F401  (registra as classes no Base)

    Base.metadata.create_all(engine)


def fabrica_de_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
