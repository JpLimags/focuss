# Focuss

Plataforma web de estudo para pessoas com TDAH: gera flashcards a partir do material do aluno,
agenda revisões com repetição espaçada (SM-2) e recompensa o esforço com XP, níveis e missões. Disciplina APS, IFCE Maracanaú.

## Estrutura
- `src/focuss/core/`: regras determinísticas (SM-2, gamificação). Sem LLM, 100% testáveis.
- `src/focuss/rag/`: extração de PDF, chunking, embeddings e geração de cartões.
- `src/focuss/dados/`: modelo do UML (SQLAlchemy) e conexão com o banco (SQLite; `FOCUSS_DB_URL` para trocar).
- `src/focuss/servicos/`: casos de uso (ex.: enviar documento). A camada web só chama esta camada.
- `src/focuss/api/`: camada web (API e telas).
- `tests/`: testes automatizados. `docs/`: requisitos, UML e wireframes.

## Rodando
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e . --no-deps
pytest && ruff check .
```

Subir a API (abre em http://127.0.0.1:8000/docs, onde dá para testar cada rota):
```bash
uvicorn focuss.api.app:criar_app --factory --reload
```
O banco fica em `data/focuss.db`. Em produção, defina `FOCUSS_SECRET_KEY`; sem ela, o login se perde a cada reinício do servidor.

## Convenções (clean code)
Funções pequenas com um propósito, nomes claros, regra de negócio fora da camada web, teste para cada regra.
Commits direto na branch `dev`, com CI verde antes de cada push. A `main` recebe só versões estáveis (entregas das sprints, com tag `sprint-N`).
