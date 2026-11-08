import pytest

from focuss.servicos.contas import ErroCadastro, autenticar, cadastrar


def test_cadastro_cria_usuario_com_perfil_e_hash(sessao):
    u = cadastrar(sessao, " Ana ", " Ana@Ex.com ", "senha-forte")
    assert u.email == "ana@ex.com"
    assert u.nome == "Ana"
    assert u.senha_hash != "senha-forte"
    assert u.senha_hash.startswith("$2")
    assert u.perfil.xp_total == 0
    assert u.perfil.nivel == 1


def test_email_duplicado(sessao):
    cadastrar(sessao, "Ana", "ana@ex.com", "senha-forte")
    with pytest.raises(ErroCadastro, match="Já existe"):
        cadastrar(sessao, "Outra", "ANA@ex.com", "senha-forte")


@pytest.mark.parametrize(
    ("nome", "email", "senha", "mensagem"),
    [
        ("", "ana@ex.com", "senha-forte", "nome"),
        ("Ana", "ana-sem-arroba", "senha-forte", "E-mail"),
        ("Ana", "ana@ex.com", "curta", "pelo menos 8"),
        ("Ana", "ana@ex.com", "x" * 73, "longa"),
    ],
)
def test_dados_invalidos(sessao, nome, email, senha, mensagem):
    with pytest.raises(ErroCadastro, match=mensagem):
        cadastrar(sessao, nome, email, senha)


def test_login(sessao):
    u = cadastrar(sessao, "Ana", "ana@ex.com", "senha-forte")
    assert autenticar(sessao, "ANA@ex.com", "senha-forte") is u
    assert autenticar(sessao, "ana@ex.com", "senha-errada") is None
    assert autenticar(sessao, "nao@existe.com", "senha-forte") is None
    assert autenticar(sessao, "ana@ex.com", "x" * 100) is None
