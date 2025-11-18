import time
from typing import List, Dict, Any

import requests
from tqdm import tqdm

from autoru_search.config import OPENSEARCH_URL, INDEX_NAME
from autoru_search.models.article import Article


def create_index():
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}"
    # если индекс есть — удаляем
    try:
        r = requests.head(url)
        if r.status_code == 200:
            requests.delete(url)
    except requests.exceptions.ConnectionError:
        raise RuntimeError("OpenSearch не запущен на http://localhost:9200")

    body = {
        "settings": {
            "analysis": {
                "filter": {
                    "ru_stop": {"type": "stop", "stopwords": "_russian_"},
                    "ru_stemmer": {"type": "stemmer", "language": "russian"},
                },
                "analyzer": {
                    "ru_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "ru_stop", "ru_stemmer"],
                    }
                },
            }
        },
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "ru_analyzer"},
                "text": {"type": "text", "analyzer": "ru_analyzer"},
                "category": {"type": "keyword"},
                "date": {"type": "date", "ignore_malformed": True},
                "url": {"type": "keyword"},
                "site": {"type": "keyword"},
                "fetched_at": {"type": "date", "ignore_malformed": True},
            }
        },
    }

    r = requests.put(url, json=body)
    r.raise_for_status()


def bulk_index(articles: List[Article], batch_size: int = 500):
    for i in tqdm(range(0, len(articles), batch_size), desc="Bulk index"):
        chunk = articles[i : i + batch_size]
        lines = []
        for a in chunk:
            meta = {"index": {"_index": INDEX_NAME}}
            doc = {
                "url": a.url,
                "title": a.title,
                "date": a.date,
                "category": a.category,
                "text": a.text,
                "site": a.site,
                "fetched_at": a.fetched_at,
            }
            lines.append(json_dumps(meta))
            lines.append(json_dumps(doc))
        payload = "\n".join(lines) + "\n"
        r = requests.post(
            f"{OPENSEARCH_URL}/_bulk",
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
        )
        r.raise_for_status()
        time.sleep(0.1)


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


def search(query: str, size: int = 10) -> Dict[str, Any]:
    body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^2", "text"],
            }
        }
    }
    r = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_search", json=body)
    r.raise_for_status()
    return r.json()
