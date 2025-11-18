import json
from typing import Iterable

from autoru_search.config import CORPUS_PATH
from autoru_search.models.article import Article


def load_corpus() -> Iterable[Article]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            yield Article(
                url=data.get("url"),
                title=data.get("title"),
                date=data.get("date"),
                category=data.get("category"),
                text=data.get("text", ""),
                site=data.get("site", "auto.ru"),
                fetched_at=data.get("fetched_at"),
            )
