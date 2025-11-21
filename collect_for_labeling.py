import csv
import json
from pathlib import Path
import requests


ES_URL = "http://localhost:9200"
INDEX_NAME = "autoru_mag"
AUTH = ("admin", "StrongPassw0rd!")


TEST_QUERIES = [
    "зимние шины",
    "новые китайские автомобили",
    "цены на автомобили 2025",
    "повышение транспортного налога",
    "электромобили в России",
    "снижение цен на бензин",
    "какие авто подорожали",
    "продажи автомобилей в России",
    "проверка vin онлайн",
    "новые штрафы для водителей"
]


def load_synonyms():
    path = Path(__file__).parent / "synonyms.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


SYN = load_synonyms()


def build_query_body(q: str) -> dict:
    syn_q = build_synonym_query(q)
    fields = ["title^3", "text"]

    should_queries = [
        {
            "multi_match": {
                "query": q,
                "fields": fields,
                "operator": "and",
                "fuzziness": "AUTO",
                "boost": 2.0
            }
        }
    ]

    if syn_q:
        should_queries.append({
            "multi_match": {
                "query": syn_q,
                "fields": fields,
                "operator": "or",
                "fuzziness": "AUTO",
                "boost": 1.5
            }
        })

    return {
        "query": {
            "bool": {
                "should": should_queries,
                "minimum_should_match": 1,
                "must_not": [
                    {"match_phrase": {"title": "Главное за день"}},
                    {"match_phrase": {"title": "главное за день"}}
                ]
            }
        }
    }


def build_synonym_query(q: str) -> str | None:
    import re
    q_norm = re.sub(r"\s+", " ", q.strip().lower())
    phrases = list(SYN.keys())
    phrases.sort(key=len, reverse=True)
    used = []
    tmp = q_norm

    for p in phrases:
        if p in tmp:
            used.extend(SYN[p])
            tmp = tmp.replace(p, " ")

    tokens = re.findall(r"\w+", tmp, flags=re.UNICODE)
    for t in tokens:
        if t in SYN:
            used.extend(SYN[t])

    if not used:
        return None
    return " ".join(sorted(set(used)))


def es_search(query: str, size: int = 10):
    body = build_query_body(query)
    r = requests.get(
        f"{ES_URL}/{INDEX_NAME}/_search",
        json=body,
        auth=AUTH,
        params={"size": size},
    )
    r.raise_for_status()
    return r.json()


def main():
    output_file = "search_results_for_labeling.csv"

    print(" Сбор результатов поиска для разметки...")
    print(f" Запросы: {len(TEST_QUERIES)}")

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Релевантность', 'Запрос', 'Заголовок', 'Текст', 'URL', 'Категория', 'Дата'])

        total_results = 0

        for query in TEST_QUERIES:
            print(f"Обрабатываю запрос: '{query}'")

            try:
                resp = es_search(query, size=10)
                hits = resp.get("hits", {}).get("hits", [])

                for hit in hits:
                    source = hit.get("_source", {})
                    text_preview = source.get("text", "")[:200] + "..." if len(
                        source.get("text", "")) > 200 else source.get("text", "")
                    writer.writerow([
                        '',
                        query,
                        source.get("title", "Без заголовка"),
                        text_preview,
                        source.get("url", ""),
                        source.get("category", ""),
                        source.get("date", "")
                    ])
                    total_results += 1

            except Exception as e:
                print(f" Ошибка для запроса '{query}': {e}")
                writer.writerow([
                    '', query,
                    f"ОШИБКА ПОИСКА: {e}",
                    "", "", "", ""
                ])

    print(f"\n Готово! Собрано {total_results} результатов")
    print(f" Файл: {output_file}")
    print("\n Инструкция по разметке:")
    print("1. Откройте CSV файл в Excel или Google Sheets")
    print("2. В столбце 'Релевантность' проставьте:")
    print("   - 1 = Релевантный результат")
    print("   - 0 = Нерелевантный результат")
    print("3. Сохраните файл")
    print("4. После разметки можно рассчитать метрики качества")


if __name__ == "__main__":
    main()