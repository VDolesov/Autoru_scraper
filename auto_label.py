import json
from pathlib import Path

import numpy as np
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer


PAIRS_PATH = Path("train_pairs.jsonl")
LABELED_PATH = Path("train_labeled.jsonl")


def cosine_sim(a, b):
    a_norm = a / (np.linalg.norm(a) + 1e-12)
    b_norm = b / (np.linalg.norm(b) + 1e-12)
    return float(np.dot(a_norm, b_norm))


def build_pair_score(query: str, title: str, text: str) -> float:
    doc_text = title or ""
    if text:
        if doc_text:
            doc_text += ". "
        doc_text += text[:600]

    if not query or not doc_text:
        return 0.0

    texts = [query, doc_text]

    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b",
        ngram_range=(1, 2),
        max_features=5000,
    )
    X = vectorizer.fit_transform(texts).toarray()
    q_vec = X[0]
    d_vec = X[1]

    sim = cosine_sim(q_vec, d_vec)
    if sim < 0:
        sim = 0.0
    if sim > 1:
        sim = 1.0
    return sim


def main():
    if not PAIRS_PATH.exists():
        print(f"Файл {PAIRS_PATH} не найден")
        return

    lines = PAIRS_PATH.read_text(encoding="utf-8").splitlines()
    print(f"Всего пар для разметки: {len(lines)}")

    labeled_count = 0

    with LABELED_PATH.open("w", encoding="utf-8") as f_out:
        for line in tqdm(lines, desc="Разметка пар"):
            line = line.strip()
            if not line:
                continue

            row = json.loads(line)
            query = row.get("query") or ""
            title = row.get("title") or ""
            text = row.get("text") or ""

            score = build_pair_score(query, title, text)
            row["label"] = score

            f_out.write(json.dumps(row, ensure_ascii=False) + "\n")
            labeled_count += 1

    print(f"Готово. Размечено пар: {labeled_count}, результат в {LABELED_PATH}")


if __name__ == "__main__":
    main()
