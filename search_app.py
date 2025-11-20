import re
import json
from pathlib import Path

import numpy as np
import urllib3
import requests
from joblib import load

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ES_URL = "https://localhost:9200"
INDEX_NAME = "autoru_mag"
AUTH = ("admin", "StrongPassw0rd!")

MODEL_PATH = Path("reranker_model.pkl")


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
    fields = ["title^2", "text"]

    base_query = {
        "multi_match": {
            "query": q,
            "fields": fields,
            "operator": "and",
            "fuzziness": "AUTO",
        }
    }

    if not syn_q:
        return {"query": base_query}

    return {
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": fields,
                            "operator": "and",
                            "fuzziness": "AUTO",
                            "boost": 2.0,
                        }
                    },
                    {
                        "multi_match": {
                            "query": syn_q,
                            "fields": fields,
                            "operator": "or",
                            "fuzziness": "AUTO",
                            "boost": 1.0,
                        }
                    },
                ]
            }
        }
    }


def es_search(query: str, size: int = 50):
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


def tokenize(text: str):
    return re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)


def build_features_for_doc(query: str, source: dict, es_score: float) -> list[float]:
    title = source.get("title") or ""
    text = source.get("text") or ""

    q_tokens = tokenize(query)
    t_tokens = tokenize(title)
    x_tokens = tokenize(text[:600])

    q_len = len(q_tokens)
    t_len = len(t_tokens)
    x_len = len(x_tokens)

    set_q = set(q_tokens)
    set_t = set(t_tokens)
    set_x = set(x_tokens)

    overlap_t = len(set_q & set_t)
    overlap_x = len(set_q & set_x)
    overlap_total = overlap_t + overlap_x

    denom = len(set_q) + 1e-9
    ratio_t = overlap_t / denom
    ratio_x = overlap_x / denom

    all_in_title = int(set_q.issubset(set_t)) if set_q else 0

    return [
        float(es_score) or 0.0,
        q_len,
        t_len,
        x_len,
        overlap_t,
        overlap_x,
        overlap_total,
        ratio_t,
        ratio_x,
        all_in_title,
    ]


def load_reranker():
    if not MODEL_PATH.exists():
        return None
    try:
        return load(MODEL_PATH)
    except Exception:
        return None


RERANKER = load_reranker()


def rerank_hits(query: str, hits: list[dict]) -> list[dict]:
    if RERANKER is None or not hits:
        return hits

    feats = []
    for h in hits:
        src = h.get("_source", {})
        es_score = float(h.get("_score", 0.0) or 0.0)
        feats.append(build_features_for_doc(query, src, es_score))

    X = np.array(feats, dtype=float)
    preds = RERANKER.predict(X)

    for h, p in zip(hits, preds):
        h["_ml_score"] = float(p)

    hits_sorted = sorted(hits, key=lambda x: x.get("_ml_score", 0.0), reverse=True)
    return hits_sorted


def main():
    if RERANKER is None:
        print("Внимание: reranker-модель не найдена, используется только OpenSearch score.")
    else:
        print("Reranker-модель загружена: результаты будут переупорядочены ML-моделью.")

    while True:
        q = input("\nЗапрос (пустой — выход): ").strip()
        if not q:
            break

        resp = es_search(q, size=50)
        hits = resp.get("hits", {}).get("hits", [])

        if not hits:
            print("Ничего не найдено :(")
            continue

        hits = rerank_hits(q, hits)
        top = hits[:10]

        for i, h in enumerate(top, 1):
            s = h.get("_source", {})
            es_score = float(h.get("_score", 0.0) or 0.0)
            ml_score = h.get("_ml_score")

            if ml_score is not None:
                score_str = f"ml_score={ml_score:.3f} | es_score={es_score:.3f}"
            else:
                score_str = f"score={es_score:.3f}"

            print(f"\n{i}. {s.get('title')}")
            print(f"   {score_str} | категория={s.get('category')} | дата={s.get('date')}")
            print(f"   {s.get('url')}")


if __name__ == "__main__":
    main()
