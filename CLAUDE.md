# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python 3.14+, uv)
- Install dependencies: `uv sync`
- Run all tests: `uv run pytest`
- Run a single test file: `uv run pytest tests/path/to/test.py`
- Run a specific test: `uv run pytest tests/path/to/test.py::test_name`
- Lint: `uv run ruff check .` (autofix: `uv run ruff check --fix .`)
- Format: `uv run ruff format .` (check: `uv run ruff format --check .`)
- Type check (strict mode): `uv run mypy src tests`
- Start FastAPI server: `uv run doubtless api` (port 8000)
- Start Celery background worker: `uv run doubtless worker`
- Build NCERT textbook vector index: `uv run doubtless index`

### Frontend (React 19, Vite, Tailwind CSS v4)
- Install dependencies: `cd frontend && npm install`
- Run dev server: `cd frontend && npm run dev` (port 3000)
- Run tests: `cd frontend && npm run test`
- Build: `cd frontend && npm run build`
- Lint: `cd frontend && npm run lint`

### Infrastructure (Docker)
- Start full stack: `docker compose up --build`
- Services: Redis (6379), API (8000), Worker, Frontend (3000)

---

## Architecture Overview

Doubtless is an interactive platform providing real-time doubt resolution across live and recorded video lectures.

### 1. Ingestion & Media Pipeline (`src/doubtless/media/`, `src/doubtless/worker/`)
- `PipelineRunner` (`media/pipeline.py`) coordinates the complete ingestion lifecycle across 4 monotonic stages:
  1. `transcoding` (0-25%): FFprobe container inspection (`probe.py`), thumbnail extraction (`extract_poster`), and HLS VOD segmentation (`transcoder.py`).
  2. `transcribing` (25-70%): 16kHz mono audio extraction and Groq Whisper API speech-to-text with hallucination filtering and automatic chunking (`transcriber.py`).
  3. `indexing` (70-85%): Relational segment storage (`transcript_repo`), 45s sliding chunk aggregation (`rag/lecture/chunker.py`), and vector embedding into ChromaDB (`rag/lecture/indexer.py`).
  4. `generating_notes` (85-100%): Concurrent generation of topic chapters, Markdown notes, quizzes, and flashcards (`study/generator.py`), persisted to `study_repo`.
- `transcode_video` (`worker/tasks.py`) is a thin Celery task adapter delegating to `PipelineRunner` with cancellation guards and Redis progress reporting.

### 2. Doubts Resolution & RAG (`src/doubtless/rag/`)
- `rag_agent` (`rag/agent.py`): Pydantic AI agent equipped with tools to search the lecture transcript (`search_lecture`), search official NCERT textbooks (`search_books`), and inspect chapter notes (`get_chapter_notes`), grounded on playhead timestamps.
- `chat_service` (`rag/chat_service.py`): Application service managing chat sessions, loading prior history, enriching prompts with temporal dialogue windows, executing SSE streaming (`chat_stream`), and persisting conversation messages.
- Vector Retrieval Engine (`rag/retrieval.py`): Generic `vector_search[T]` function executing bilingual query expansion (`query_expansion.py`), batch embedding (`embeddings.py`), ChromaDB querying, distance threshold filtering, and deduplication.

### 3. Study Generation (`src/doubtless/study/`)
- `generator.py`: Deep module containing Pydantic AI agents for chapters, notes, quizzes, and flashcards. Exposes pure generation functions that transform transcripts into domain models without performing side-effect database writes.
- `context.py`: Builds structured prompt contexts and extracts temporal transcript windows around the current video playhead.

### 4. Storage & Persistence (`src/doubtless/storage/`)
- SQLite (`connection.py`, `schema.py`): Primary store operating in WAL mode with foreign key cascade deletions.
- Repositories (`storage/repositories/`): Specialized data access modules for videos, transcripts, study artifacts, and chat messages.
- ChromaDB (`vector_store.py`): Persistent vector store maintaining `lectures` and `ncert` collections (cosine distance).
- Redis (`redis_store.py`): Real-time transcode stage progress tracking and cancellation signals.
- Filesystem (`file_storage.py`): Directory structure for raw uploads, HLS streams, poster images, and extracted audio.
- Cascade Teardown (`cascade_delete.py`): Multi-layer deletion purging Celery tasks, Redis keys, ChromaDB embeddings, filesystem files, and SQLite records.
