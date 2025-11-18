import json
import random
import re
from pathlib import Path


INPUT_PATH = Path("data_auto.jsonl")
OUTPUT_PATH = Path("train_queries.jsonl")
MAX_QUERIES = 1000
RANDOM_SEED = 42


def normalize_title(title: str) -> str:
    if not title:
        return ""

    t = title.strip()

    t = re.sub(r"\. Главное за день.*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"главное за день.*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)

    return t.strip()


def collect_candidate_queries() -> list[str]:
    titles = set()

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            title = obj.get("title")
            if not title:
                continue

            q = normalize_title(title)
            if not q:
                continue

            if len(q) < 15 or len(q) > 90:
                continue

            titles.add(q)

    return list(titles)


def main():
    if not INPUT_PATH.exists():
        print(f"Файл {INPUT_PATH} не найден. Убедись, что data_auto.jsonl лежит в корне проекта.")
        return

    candidates = collect_candidate_queries()
    print(f"Найдено кандидатов для запросов: {len(candidates)}")

    if not candidates:
        print("Кандидатов нет, проверь формат data_auto.jsonl")
        return

    random.seed(RANDOM_SEED)
    random.shuffle(candidates)

    selected = candidates[:MAX_QUERIES]
    print(f"Выбрано запросов: {len(selected)} (ограничение MAX_QUERIES = {MAX_QUERIES})")

    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        for i, q in enumerate(selected, start=1):
            row = {"id": i, "query": q}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Готово. Запросы сохранены в {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
