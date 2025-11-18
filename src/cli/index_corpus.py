from autoru_search.storage.json_storage import load_corpus
from autoru_search.search.opensearch_client import create_index, bulk_index


def main():
    print("Загружаю корпус из JSONL...")
    articles = list(load_corpus())
    print(f"Всего статей: {len(articles)}")

    print("Создаю индекс...")
    create_index()

    print("Индексирую документы...")
    bulk_index(articles)

    print("Готово.")


if __name__ == "__main__":
    main()
