# doubtless

An interactive platform providing real-time doubt resolution across live and recorded video lectures.

## Use it

Needs [uv](https://docs.astral.sh/uv/) and Python 3.14+. `uv sync` fetches the
interpreter if you don't already have one.

| Command | |
| --- | --- |
| `uv sync` | create `.venv` and install dependencies |
| `uv run doubtless api` | run the FastAPI server (default: port 8000) |
| `uv run doubtless worker` | run the Celery background worker |
| `uv run doubtless index` | build NCERT textbook vector index |
| `uv run ruff check --fix .` | lint |
| `uv run ruff format .` | format |
| `uv run mypy` | type-check (strict mode) |

### Architecture Layout

| Path | Responsibility |
| --- | --- |
| `src/doubtless/api/` | FastAPI presentation layer: modular REST routers and streaming upload manager |
| `src/doubtless/domain/` | Pydantic schemas and domain type definitions |
| `src/doubtless/storage/` | Persistence: SQLite engine (WAL mode) and filesystem layout |
| `src/doubtless/media/` | Domain services: FFprobe inspection, FFmpeg command builder, non-blocking progress parser & cancellation |
| `src/doubtless/worker/` | Asynchronous Celery tasks for media transcoding |
| `src/doubtless/rag/` | Knowledge retrieval & doubt resolution agent |

### Dependencies

`uv add <pkg>` for runtime, `uv add --dev <pkg>` for tooling. Both write to
`uv.lock`, which is committed so every clone resolves to the same versions.

### Hooks

The pre-commit hooks shell out to `uv run ruff` and `uv run mypy` rather than
pinning versions of their own. There is one of each, the ones in the `dev`
group, so a hook can never disagree with what you run by hand. Bump them with
`uv add --dev ruff@latest mypy@latest` and both sides move together.

mypy runs in `strict` mode over `src`. Loosen it
in the `[tool.mypy]` block if a dependency ships no stubs.
