from doubtless.rag.index import build_index
from doubtless.rag.retrieve import search


def main() -> None:
    build_index()
    res = search("what is pythjagoral theorem ?")
    print(res)


if __name__ == "__main__":
    main()
