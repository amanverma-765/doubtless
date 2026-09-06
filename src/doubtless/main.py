from doubtless.rag.agent import rag_agent
from doubtless.rag.index import build_index


def main() -> None:
    build_index()
    rag_agent.to_cli_sync("what is pythagorous threorem")


if __name__ == "__main__":
    main()
