import json
from pathlib import Path

import urllib3
import requests

from search_app import build_query_body, ES_URL, INDEX_NAME, AUTH

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

QUERIES_PATH = Path("train_queries.jsonl")
PAIRS_PATH = Path("train_pairs.jsonl")
TOP_K = 10


def search_raw(query: str, size: int = TOP_K):
    body = build_query_body(query)
    r = requests.get(
        f"{ES_URL}/{INDEX_NAME}/_search",
        json=body,
        auth=AUTH,
        verify=False,
        params={"size": size},
    )
    r.raise_for_status()
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    return hits


def main():
    if not QUERIES_PATH.exists():
        print(f"Файл {QUERIES_PATH} не найден")
        return

    total_pairs = 0
    with QUERIES_PATH.open("r", encoding="utf-8") as f_in, PAIRS_PATH.open(
        "w", encoding="utf-8"
    ) as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            q_id = row.get("id")
            query = row.get("query")
            if not query:
                continue

            hits = search_raw(query, size=TOP_K)
            for rank, h in enumerate(hits, start=1):
                src = h.get("_source", {})
                url = src.get("url")
                title = src.get("title")
                text = src.get("text")
                category = src.get("category")
                date = src.get("date")
                es_score = h.get("_score", 0)

                pair = {
                    "query_id": q_id,
                    "query": query,
                    "doc_url": url,
                    "title": title,
                    "text": text,
                    "category": category,
                    "date": date,
                    "es_score": es_score,
                    "rank": rank,
                }
                f_out.write(json.dumps(pair, ensure_ascii=False) + "\n")
                total_pairs += 1

    print(f"Готово. Сохранено пар: {total_pairs} в {PAIRS_PATH}")


if __name__ == "__main__":
    main()