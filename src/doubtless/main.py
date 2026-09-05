from doubtless.rag.retrieve import search


def main() -> None:
    print("Hello World")
    res = search("what is pythjagoral theorem ?")
    print(res)


if __name__ == "__main__":
    main()
