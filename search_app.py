import re
import json
from pathlib import Path
import requests

ES_URL = "http://localhost:9200"
INDEX_NAME = "autoru_mag"
AUTH = ("admin", "StrongPassw0rd!")


SYNONYMS_FILE = Path("synonyms.json")
SPELLFIX_FILE = Path("spellfix.json")


def load_json_file(file_path: Path) -> dict:

    if not file_path.exists():
        print(f"[WARN] Файл не найден: {file_path}")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки {file_path}: {e}")
        return {}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def apply_spellfix(text: str, spellfix: dict[str, str]) -> str:
    if not isinstance(text, str):
        return text

    fixed_text = text
    phrases = sorted(spellfix.keys(), key=len, reverse=True)

    for phrase in phrases:
        if phrase in fixed_text:
            fixed_text = fixed_text.replace(phrase, spellfix[phrase])

    return fixed_text


def expand_synonyms(text: str, synonyms: dict[str, list[str]]) -> list[str]:
    tokens = normalize_text(text).split()
    expanded = []

    for token in tokens:
        expanded.append(token)
        if token in synonyms:
            expanded.extend(synonyms[token])

    return sorted(set(expanded))


def build_synonym_query(q: str, synonyms: dict) -> str | None:
    q_norm = normalize_text(q)
    expanded_tokens = expand_synonyms(q_norm, synonyms)

    if len(expanded_tokens) <= 1:
        return None

    return " ".join(expanded_tokens)


def build_query_body(q: str, synonyms: dict, spellfix: dict) -> dict:

    q_norm = normalize_text(q)
    q_fixed = apply_spellfix(q_norm, spellfix)


    syn_q = build_synonym_query(q_fixed, synonyms)

    fields = ["title^4", "text"]
    should_queries = []

    should_queries.append({
        "multi_match": {
            "query": q_fixed,
            "fields": fields,
            "operator": "and",
            "fuzziness": "AUTO",
            "boost": 2.0
        }
    })

    year_match = re.search(r'\b(202[4-7])\b', q_fixed)
    if year_match:
        year = year_match.group(1)
        should_queries.append({
            "match_phrase": {
                "title": {
                    "query": year,
                    "boost": 5.0
                }
            }
        })

    if any(term in q_fixed for term in ['vin', 'vincode', 'vin-код', 'вин']):
        should_queries.extend([
            {
                "match_phrase": {
                    "title": {
                        "query": "vin",
                        "boost": 6.0
                    }
                }
            },
            {
                "match_phrase": {
                    "text": {
                        "query": "vin",
                        "boost": 4.0
                    }
                }
            }
        ])

    if syn_q and syn_q != q_fixed:
        should_queries.append({
            "multi_match": {
                "query": syn_q,
                "fields": fields,
                "operator": "or",
                "fuzziness": "AUTO",
                "boost": 1.8
            }
        })

    must_not = [
        {"match_phrase": {"title": "Главное за день"}},
        {"match_phrase": {"title": "главное за день"}}
    ]

    # Умные исключения
    if any(word in q_fixed for word in ['снижение', 'падение', 'дешевеет']):
        must_not.extend([
            {"match": {"title": "рост"}},
            {"match": {"title": "подорожание"}},
            {"match": {"title": "увеличились"}}
        ])

    if any(word in q_fixed for word in ['бензин', 'топливо', 'бензиновый']):
        must_not.extend([
            {"match": {"text": "электромобиль"}},
            {"match": {"text": "электроcar"}},
            {"match": {"text": "tesla"}}
        ])


    if any(word in q_fixed for word in ['цена', 'цены', 'стоимость', 'прайс']):
        should_queries.append({
            "match": {
                "title": {
                    "query": "цена",
                    "boost": 3.0
                }
            }
        })

    return {
        "query": {
            "bool": {
                "should": should_queries,
                "minimum_should_match": 1,
                "must_not": must_not
            }
        }
    }


def es_search(query: str, synonyms: dict, spellfix: dict, size: int = 30):
    body = build_query_body(query, synonyms, spellfix)
    r = requests.get(
        f"{ES_URL}/{INDEX_NAME}/_search",
        json=body,
        auth=AUTH,
        params={"size": size},
    )
    r.raise_for_status()
    return r.json()


def main():
    print("=== Auto.ru Search (Enhanced) ===")
    print("Синонимы + Исправления опечаток + Умный поиск")

    synonyms = load_json_file(SYNONYMS_FILE)
    spellfix = load_json_file(SPELLFIX_FILE)

    print(f"Загружено синонимов: {len(synonyms)}")
    print(f"Загружено исправлений: {len(spellfix)}")

    while True:
        q = input("\n Запрос (пустой - выход): ").strip()
        if not q:
            break

        try:
            resp = es_search(q, synonyms, spellfix, size=30)
            hits = resp.get("hits", {}).get("hits", [])

            if not hits:
                print(" Ничего не найдено")
                continue

            print(f"\n Найдено результатов: {len(hits)}")

            for i, h in enumerate(hits, 1):
                s = h.get("_source", {})
                score = float(h.get("_score", 0.0) or 0.0)

                print(f"\n{i}. {s.get('title', 'Без заголовка')}")
                print(f"   score: {score:.3f} | категория: {s.get('category', 'Не указана')}")
                print(f"   дата: {s.get('date', 'Не указана')}")
                if s.get('url'):
                    print(f"   {s.get('url')}")

        except Exception as e:
            print(f"Ошибка поиска: {e}")


if __name__ == "__main__":
    main()