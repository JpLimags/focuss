"""Classes do UML: Usuario, Documento, Trecho, Flashcard, Agendamento, RespostaCartao,
PerfilJogador.

As regras (SM-2, XP, nível) ficam em focuss.core; aqui só há persistência e a ponte
entre o registro do banco e os objetos de domínio.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from focuss.core import sm2
from focuss.core.gamification import nivel_do_xp
from focuss.core.sm2 import Botao
from focuss.dados.banco import Base


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class StatusCartao(enum.Enum):
    RASCUNHO = "rascunho"
    APROVADO = "aprovado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    modo_foco: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    documentos: Mapped[list[Documento]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    perfil: Mapped[PerfilJogador] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )


class Documento(Base):
    """PDF enviado. Guardamos só o texto extraído, não o arquivo."""

    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    num_paginas: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)
    enviado_em: Mapped[datetime] = mapped_column(default=_agora)

    usuario: Mapped[Usuario] = relationship(back_populates="documentos")
    trechos: Mapped[list[Trecho]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Trecho.ordem",
    )
    flashcards: Mapped[list[Flashcard]] = relationship(
        back_populates="documento", cascade="all, delete-orphan", passive_deletes=True
    )


class Trecho(Base):
    """Pedaço do documento usado na recuperação (chunking na Sprint 3)."""

    __tablename__ = "trechos"
    __table_args__ = (UniqueConstraint("documento_id", "ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id", ondelete="CASCADE"))
    ordem: Mapped[int]
    pagina: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)

    documento: Mapped[Documento] = relationship(back_populates="trechos")


class Flashcard(Base):
    """Cartão gerado. Sempre aponta para o trecho de origem (RF08)."""

    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id", ondelete="CASCADE"))
    trecho_id: Mapped[int] = mapped_column(ForeignKey("trechos.id", ondelete="CASCADE"))
    pergunta: Mapped[str] = mapped_column(Text)
    resposta: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusCartao] = mapped_column(Enum(StatusCartao), default=StatusCartao.RASCUNHO)
    criado_em: Mapped[datetime] = mapped_column(default=_agora)

    documento: Mapped[Documento] = relationship(back_populates="flashcards")
    trecho: Mapped[Trecho] = relationship()
    agendamento: Mapped[Agendamento | None] = relationship(
        back_populates="flashcard", cascade="all, delete-orphan", passive_deletes=True
    )
    respostas: Mapped[list[RespostaCartao]] = relationship(
        back_populates="flashcard", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def aprovado(self) -> bool:
        return self.status is StatusCartao.APROVADO

    def aprovar(self, hoje: date) -> None:
        """Cartão só entra em revisão após aprovado (RF09-10): cria o agendamento aqui."""
        if self.aprovado:
            return
        self.status = StatusCartao.APROVADO
        self.agendamento = Agendamento()
        self.agendamento.aplicar(sm2.Agendamento(proxima_revisao=hoje))


class Agendamento(Base):
    """Estado SM-2 de um cartão aprovado."""

    __tablename__ = "agendamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(
        ForeignKey("flashcards.id", ondelete="CASCADE"), unique=True
    )
    repeticoes: Mapped[int] = mapped_column(default=0)
    intervalo_dias: Mapped[int] = mapped_column(default=0)
    fator_facilidade: Mapped[float] = mapped_column(default=sm2.EF_INICIAL)
    proxima_revisao: Mapped[date | None] = mapped_column(index=True)

    flashcard: Mapped[Flashcard] = relationship(back_populates="agendamento")

    def para_dominio(self) -> sm2.Agendamento:
        return sm2.Agendamento(
            repeticoes=self.repeticoes,
            intervalo_dias=self.intervalo_dias,
            fator_facilidade=self.fator_facilidade,
            proxima_revisao=self.proxima_revisao,
        )

    def aplicar(self, novo: sm2.Agendamento) -> None:
        self.repeticoes = novo.repeticoes
        self.intervalo_dias = novo.intervalo_dias
        self.fator_facilidade = novo.fator_facilidade
        self.proxima_revisao = novo.proxima_revisao


class RespostaCartao(Base):
    """Histórico de respostas: base para o resumo da sessão e para o anti-farm."""

    __tablename__ = "respostas_cartao"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id", ondelete="CASCADE"))
    botao: Mapped[Botao] = mapped_column(Enum(Botao))
    revisao_agendada: Mapped[bool]
    xp_ganho: Mapped[int] = mapped_column(default=0)
    respondido_em: Mapped[datetime] = mapped_column(default=_agora)

    flashcard: Mapped[Flashcard] = relationship(back_populates="respostas")


class PerfilJogador(Base):
    """XP, sequência e dados de jogo. O nível é sempre derivado do XP, nunca gravado."""

    __tablename__ = "perfis_jogador"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    xp_total: Mapped[int] = mapped_column(default=0)
    sequencia: Mapped[int] = mapped_column(default=0)
    ultimo_dia_estudo: Mapped[date | None]

    usuario: Mapped[Usuario] = relationship(back_populates="perfil")

    @property
    def nivel(self) -> int:
        return nivel_do_xp(self.xp_total)
