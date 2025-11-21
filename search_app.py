import re
import json
from pathlib import Path
import requests

ES_URL = "http://localhost:9200"
INDEX_NAME = "autoru_mag"
AUTH = ("admin", "StrongPassw0rd!")


def load_synonyms():
    path = Path(__file__).parent / "synonyms.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


SYN = load_synonyms()


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def build_synonym_query(q: str) -> str | None:
    q_norm = normalize_query(q)
    phrases = list(SYN.keys())
    phrases.sort(key=len, reverse=True)
    used: list[str] = []
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


def build_query_body(q: str) -> dict:
    syn_q = build_synonym_query(q)
    print(f" DEBUG: Запрос '{q}' → синонимы: {syn_q}")
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
                    {
                        "match_phrase": {
                            "title": "Главное за день"
                        }
                    },
                    {
                        "match_phrase": {
                            "title": "главное за день"
                        }
                    }
                ]
            }
        }
    }

def es_search(query: str, size: int = 30):
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
    print("=== Auto.ru Search ===")
    print("Поиск по автомобильным статьям")

    while True:
        q = input("\n Запрос (пустой - выход): ").strip()
        if not q:
            break

        try:
            resp = es_search(q, size=30)
            hits = resp.get("hits", {}).get("hits", [])

            if not hits:
                print(" Ничего не найдено")
                continue

            print(f"\n Найдено результатов: {len(hits)}")

            for i, h in enumerate(hits, 1):
                s = h.get("_source", {})
                score = float(h.get("_score", 0.0) or 0.0)

                print(f"\n{i}. {s.get('title', 'Без заголовка')}")
                print(f"   score: {score:.3f} |  категория: {s.get('category', 'Не указана')}")
                print(f"    дата: {s.get('date', 'Не указана')}")
                if s.get('url'):
                    print(f"   {s.get('url')}")

        except Exception as e:
            print(f"Ошибка поиска: {e}")


if __name__ == "__main__":
    main()