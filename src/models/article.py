from dataclasses import dataclass
from typing import Optional


@dataclass
class Article:
    url: str
    title: Optional[str]
    date: Optional[str]
    category: Optional[str]
    text: str
    site: str
    fetched_at: Optional[str] = None
