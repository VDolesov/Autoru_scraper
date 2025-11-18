import re
import json
import urllib3
import requests
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ES_URL = "https://localhost:9200"
INDEX_NAME = "autoru_mag"
AUTH = ("admin", "StrongPassw0rd!")

def load_synonyms():
    path = Path(__file__).parent / "synonyms.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

SYN = load_synonyms()

def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())

def build_synonym_query(q: str) -> str | None:
    q_norm = normalize_query(q)
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

def build_query_body(q: str) -> dict:
    syn_q = build_synonym_query(q)
    fields = ["title^2", "text"]
    if not syn_q:
        return {"query": {"multi_match": {"query": q, "fields": fields}}}
    return {
        "query": {
            "bool": {
                "should": [
                    {"multi_match": {"query": q, "fields": fields, "boost": 2.0}},
                    {"multi_match": {"query": syn_q, "fields": fields, "boost": 1.0}}
                ]
            }
        }
    }

def search(query: str, size: int = 10):
    body = build_query_body(query)
    r = requests.get(
        f"{ES_URL}/{INDEX_NAME}/_search",
        json=body,
        auth=AUTH,
        verify=False,
        params={"size": size},
    )
    r.raise_for_status()
    return r.json()

def main():
    while True:
        q = input("\nЗапрос (пустой — выход): ").strip()
        if not q:
            break
        resp = search(q)
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            print("Ничего не найдено :(")
            continue
        for i, h in enumerate(hits, 1):
            s = h.get("_source", {})
            score = h.get("_score", 0) or 0
            print(f"\n{i}. {s.get('title')}")
            print(f"   score={score:.3f} | категория={s.get('category')} | дата={s.get('date')}")
            print(f"   {s.get('url')}")

if __name__ == "__main__":
    main()
