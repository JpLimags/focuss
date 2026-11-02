# Focuss

Plataforma web de estudo para pessoas com TDAH: gera flashcards a partir do material do aluno,
agenda revisões com repetição espaçada (SM-2) e recompensa o esforço com XP, níveis e missões. Disciplina APS, IFCE Maracanaú.

## Estrutura
- `src/focuss/core/`: regras determinísticas (SM-2, gamificação). Sem LLM, 100% testáveis.
- `src/focuss/rag/`: extração de PDF, chunking, embeddings e geração de cartões.
- `src/focuss/api/`: camada web (API e telas).
- `tests/`: testes automatizados. `docs/`: requisitos, UML e wireframes.

## Rodando
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check .
```

## Convenções (clean code)
Commits direto na branch `dev`, com CI verde antes de cada push. A `main` recebe só versões estáveis (entregas das sprints).
