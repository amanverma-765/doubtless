"""CLI entrypoint for Doubtless backend services."""

import sys

import uvicorn

from doubtless.config import HOST, PORT


def main() -> None:
    """Entrypoint for the `doubtless` CLI script."""
    command = sys.argv[1] if len(sys.argv) > 1 else "api"

    if command in ("api", "serve"):
        print(f"Starting doubtless API server on {HOST}:{PORT}...")
        uvicorn.run("doubtless.api.app:app", host=HOST, port=PORT, reload=False)
    elif command == "worker":
        # Lazy import to avoid Celery startup overhead on other subcommands
        from doubtless.worker.celery_app import celery_app

        print("Starting doubtless Celery worker...")
        celery_app.worker_main(["worker", "--loglevel=info", "--concurrency=1"])
    elif command == "index":
        # Lazy import to avoid ~3s PyTorch overhead on api/worker
        from doubtless.rag.index import build_index

        print("Building NCERT vector index...")
        build_index()
    else:
        print(f"Unknown command: {command}")
        print("Usage: doubtless [api|worker|index]")
        sys.exit(1)


if __name__ == "__main__":
    main()
