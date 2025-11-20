import json
import re
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from joblib import dump

LABELED_PATH = Path("train_labeled.jsonl")
MODEL_PATH = Path("reranker_model.pkl")


def tokenize(text: str):
    return re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)


def build_features_row(row: dict) -> list[float]:
    query = row.get("query") or ""
    title = row.get("title") or ""
    text = row.get("text") or ""

    es_score = float(row.get("es_score", 0.0) or 0.0)

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
        es_score,      # 0
        q_len,         # 1
        t_len,         # 2
        x_len,         # 3
        overlap_t,     # 4
        overlap_x,     # 5
        overlap_total, # 6
        ratio_t,       # 7
        ratio_x,       # 8
        all_in_title,  # 9
    ]


def main():
    if not LABELED_PATH.exists():
        print(f"Файл {LABELED_PATH} не найден")
        return

    lines = LABELED_PATH.read_text(encoding="utf-8").splitlines()
    print(f"Читаю размеченные пары: {len(lines)}")

    X = []
    y = []

    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        label = float(row.get("label", 0.0) or 0.0)
        feats = build_features_row(row)
        X.append(feats)
        y.append(label)

    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_val)
    mse = mean_squared_error(y_val, pred)
    print(f"Validation MSE: {mse:.4f}")

    dump(model, MODEL_PATH)
    print(f"Модель сохранена в {MODEL_PATH}")


if __name__ == "__main__":
    main()
