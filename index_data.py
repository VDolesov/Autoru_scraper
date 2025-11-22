import json
import time
import requests
from tqdm import tqdm

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ES_URL = "http://localhost:9200"
INDEX_NAME = "autoru_mag"
DATA_FILE = "data_auto.jsonl"
AUTH = ("admin", "StrongPassw0rd!")


def create_index():
    url = f"{ES_URL}/{INDEX_NAME}"
    try:
        resp = requests.head(url, auth=AUTH)
        if resp.status_code == 200:
            requests.delete(url, auth=AUTH)
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

    r = requests.put(url, json=body, auth=AUTH)
    r.raise_for_status()


def bulk_index():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        docs = [json.loads(line) for line in f if line.strip()]

    batch_size = 500
    for i in tqdm(range(0, len(docs), batch_size), desc="Bulk index"):
        chunk = docs[i : i + batch_size]
        lines = []
        for doc in chunk:
            meta = {"index": {"_index": INDEX_NAME}}
            lines.append(json.dumps(meta, ensure_ascii=False))
            lines.append(json.dumps(doc, ensure_ascii=False))
        payload = "\n".join(lines) + "\n"
        r = requests.post(
            f"{ES_URL}/_bulk",
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/x-ndjson"},
            auth=AUTH
        )
        r.raise_for_status()
        time.sleep(0.1)


if __name__ == "__main__":
    create_index()
    bulk_index()