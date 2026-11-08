"""Banco SQLite do Focuss (esquema derivado do diagrama de classes)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    duracao_sessao_min INTEGER NOT NULL DEFAULT 15,
    limite_novos_por_dia INTEGER NOT NULL DEFAULT 10
);
CREATE TABLE IF NOT EXISTS documento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROCESSANDO'
        CHECK (status IN ('PROCESSANDO', 'PRONTO', 'ERRO')),
    mensagem_erro TEXT,
    enviado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS trecho (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL,
    pagina INTEGER NOT NULL,
    texto TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flashcard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trecho_id INTEGER REFERENCES trecho(id) ON DELETE SET NULL,
    documento_id INTEGER NOT NULL REFERENCES documento(id) ON DELETE CASCADE,
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'RASCUNHO'
        CHECK (estado IN ('RASCUNHO', 'APROVADO', 'SINALIZADO')),
    manual INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS agendamento (
    flashcard_id INTEGER PRIMARY KEY REFERENCES flashcard(id) ON DELETE CASCADE,
    repeticoes INTEGER NOT NULL DEFAULT 0,
    intervalo_dias INTEGER NOT NULL DEFAULT 0,
    fator_facilidade REAL NOT NULL DEFAULT 2.5,
    proxima_revisao TEXT
);
CREATE TABLE IF NOT EXISTS resposta_cartao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flashcard_id INTEGER NOT NULL REFERENCES flashcard(id) ON DELETE CASCADE,
    nota INTEGER NOT NULL CHECK (nota BETWEEN 0 AND 5),
    xp_concedido INTEGER NOT NULL DEFAULT 0,
    respondido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS perfil_jogador (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuario(id) ON DELETE CASCADE,
    xp_total INTEGER NOT NULL DEFAULT 0,
    sequencia_atual INTEGER NOT NULL DEFAULT 0,
    melhor_sequencia INTEGER NOT NULL DEFAULT 0,
    ultimo_dia_estudo TEXT,
    modo_foco INTEGER NOT NULL DEFAULT 0
);
"""


def conectar(caminho: str | Path = ":memory:") -> sqlite3.Connection:
    """Abre o banco, ativa chaves estrangeiras e cria as tabelas se faltarem."""
    conexao = sqlite3.connect(str(caminho))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript(ESQUEMA)
    return conexao
