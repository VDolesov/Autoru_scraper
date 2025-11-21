import csv
import json
from pathlib import Path
import requests
import re

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
    fields = ["title^4", "text"]

    # ОСНОВНОЕ УЛУЧШЕНИЕ: Разные стратегии для разных типов запросов
    q_lower = q.lower()

    # 1. Для запросов про бензин - упрощенная логика
    if any(word in q_lower for word in ['бензин', 'топливо']):
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": "бензин топливо цена стоимость",
                                "fields": fields,
                                "operator": "or",
                                "boost": 2.0
                            }
                        },
                        {
                            "match": {
                                "title": {
                                    "query": "бензин",
                                    "boost": 3.0
                                }
                            }
                        },
                        {
                            "match": {
                                "title": {
                                    "query": "топливо",
                                    "boost": 2.0
                                }
                            }
                        }
                    ],
                    "must_not": [
                        {"match_phrase": {"title": "Главное за день"}},
                        {"match_phrase": {"title": "главное за день"}},
                        {"match": {"title": "электромобиль"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }

    # 2. Для запросов про VIN - агрессивный поиск
    elif any(term in q_lower for term in ['vin', 'вин', 'vincode']):
        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": "vin номер идентификационный кузовной",
                                "fields": fields,
                                "operator": "or",
                                "boost": 3.0
                            }
                        },
                        {
                            "match_phrase": {
                                "text": {
                                    "query": "vin",
                                    "boost": 4.0
                                }
                            }
                        },
                        {
                            "wildcard": {
                                "title": {
                                    "value": "*vin*",
                                    "boost": 5.0
                                }
                            }
                        }
                    ],
                    "must_not": [
                        {"match_phrase": {"title": "Главное за день"}},
                        {"match_phrase": {"title": "главное за день"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }

    # 3. Для запросов с годами и ценами - комбинированный поиск
    elif any(word in q_lower for word in ['цена', 'цены', 'стоимость']) and re.search(r'\b(202[4-7])\b', q):
        year_match = re.search(r'\b(202[4-7])\b', q)
        year = year_match.group(1) if year_match else ""

        return {
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "must": [
                                    {"match": {"title": "цена"}},
                                    {"match": {"title": year}}
                                ],
                                "boost": 4.0
                            }
                        },
                        {
                            "bool": {
                                "must": [
                                    {"match": {"title": "стоимость"}},
                                    {"match": {"title": year}}
                                ],
                                "boost": 4.0
                            }
                        },
                        {
                            "multi_match": {
                                "query": f"цена стоимость {year}",
                                "fields": fields,
                                "operator": "or",
                                "boost": 2.0
                            }
                        }
                    ],
                    "must_not": [
                        {"match_phrase": {"title": "Главное за день"}},
                        {"match_phrase": {"title": "главное за день"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }

    # 4. ОБЩАЯ ЛОГИКА для остальных запросов
    else:
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

        # Временной контекст для любых запросов с годами
        year_match = re.search(r'\b(202[4-7])\b', q)
        if year_match:
            year = year_match.group(1)
            should_queries.append({
                "match_phrase": {
                    "title": {
                        "query": year,
                        "boost": 3.0
                    }
                }
            })

        # Добавляем синонимы если есть
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
    output_file = "search_results_after_improvements.csv"

    print("🔍 Сбор результатов ПОСЛЕ улучшений...")
    print(f"📝 Запросы: {len(TEST_QUERIES)}")

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
                        '',  # Релевантность - пустое поле для ручной разметки
                        query,
                        source.get("title", "Без заголовка"),
                        text_preview,
                        source.get("url", ""),
                        source.get("category", ""),
                        source.get("date", "")
                    ])
                    total_results += 1

            except Exception as e:
                print(f"❌ Ошибка для запроса '{query}': {e}")
                writer.writerow(['', query, f"ОШИБКА: {e}", "", "", "", ""])

    print(f"\n✅ Готово! Собрано {total_results} результатов после улучшений")
    print(f"📁 Файл: {output_file}")


if __name__ == "__main__":
    main()