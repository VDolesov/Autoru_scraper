from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
CORPUS_PATH = DATA_DIR / "data_auto.jsonl"

OPENSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "autoru_mag"
