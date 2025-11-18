from autoru_search.search.opensearch_client import search


def main():
    while True:
        q = input("\nЗапрос (пусто = выход): ").strip()
        if not q:
            break

        resp = search(q, size=10)
        hits = resp.get("hits", {}).get("hits", [])

        for i, h in enumerate(hits, 1):
            src = h.get("_source", {})
            score = h.get("_score")
            print(f"\n{i}. {src.get('title')}")
            print(f"   score={score:.3f} | категория={src.get('category')} | дата={src.get('date')}")
            print(f"   {src.get('url')}")

        if not hits:
            print("Ничего не найдено :(")


if __name__ == "__main__":
    main()
