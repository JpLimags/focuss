"""Caso de uso: cadastro e login (RF01). Senha guardada só como hash bcrypt."""

from __future__ import annotations

import re

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from focuss.dados.modelos import PerfilJogador, Usuario

SENHA_MINIMA = 8
SENHA_MAXIMA_BYTES = 72  # limite do bcrypt
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Hash usado quando o e-mail não existe, para o login levar o mesmo tempo nos dois casos.
_HASH_FICTICIO = bcrypt.hashpw(b"senha-ficticia", bcrypt.gensalt()).decode()


class ErroCadastro(Exception):
    """Erro com mensagem pronta para mostrar ao aluno."""


def cadastrar(sessao: Session, nome: str, email: str, senha: str) -> Usuario:
    nome, email = nome.strip(), _normalizar_email(email)
    if not nome:
        raise ErroCadastro("Informe seu nome.")
    if not _EMAIL.match(email):
        raise ErroCadastro("E-mail inválido.")
    _validar_senha(senha)
    if sessao.scalar(select(Usuario.id).where(Usuario.email == email)) is not None:
        raise ErroCadastro("Já existe uma conta com este e-mail.")

    usuario = Usuario(nome=nome, email=email, senha_hash=_gerar_hash(senha))
    usuario.perfil = PerfilJogador(xp_total=0, sequencia=0)
    sessao.add(usuario)
    sessao.flush()
    return usuario


def autenticar(sessao: Session, email: str, senha: str) -> Usuario | None:
    """Devolve o usuário se e-mail e senha conferem; None caso contrário."""
    usuario = sessao.scalar(select(Usuario).where(Usuario.email == _normalizar_email(email)))
    hash_salvo = usuario.senha_hash if usuario else _HASH_FICTICIO
    senha_ok = _conferir(senha, hash_salvo)
    return usuario if usuario and senha_ok else None


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def _validar_senha(senha: str) -> None:
    if len(senha) < SENHA_MINIMA:
        raise ErroCadastro(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
    if len(senha.encode()) > SENHA_MAXIMA_BYTES:
        raise ErroCadastro("A senha é longa demais.")


def _gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def _conferir(senha: str, hash_salvo: str) -> bool:
    dados = senha.encode()
    if len(dados) > SENHA_MAXIMA_BYTES:
        return False
    return bcrypt.checkpw(dados, hash_salvo.encode())
