import json
import os
import time
import random
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


URLS_FILE = "urls_auto.txt"
OUT_FILE = "src/storage/data_auto.jsonl"
MIN_CHARS = 400
TARGET_DOCS = 6000      # по максимуму


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--headless=new")  # можно раскомментировать, чтобы браузер не показывался

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def parse_article_html(html: str, url: str, min_chars: int):
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    if not title_tag:
        title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    date = None
    time_tag = soup.find("time")
    if time_tag:
        raw = time_tag.get("datetime") or time_tag.get_text(strip=True)
        try:
            date = dtparse(raw).isoformat()
        except Exception:
            date = raw

    category = None
    meta_section = soup.find("meta", attrs={"property": "article:section"})
    if meta_section:
        category = meta_section.get("content")

    # самый надёжный вариант: берём весь текст страницы
    text = soup.get_text(" ", strip=True)

    if not text or len(text) < min_chars:
        return None

    result = {
        "url": url,
        "title": title,
        "date": date,
        "author": None,
        "category": category,
        "tags": None,
        "text": text,
        "site": "auto.ru",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    return result


def load_urls():
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    urls = list(dict.fromkeys(urls))
    return urls


def load_processed_urls():
    processed = set()
    if not os.path.exists(OUT_FILE):
        return processed

    with open(OUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                url = data.get("url")
                if url:
                    processed.add(url)
            except json.JSONDecodeError:
                continue
    return processed


def main():
    urls = load_urls()
    print(f"Всего URL в списке: {len(urls)}")

    processed_urls = load_processed_urls()
    print(f"Уже сохранено документов: {len(processed_urls)}")

    to_process = [u for u in urls if u not in processed_urls]
    print(f"Осталось обработать URL: {len(to_process)}")

    driver = setup_driver()

    saved = len(processed_urls)
    total_target = min(TARGET_DOCS, len(urls))

    pbar = tqdm(total=max(0, total_target - saved), desc="Скачивание статей (Selenium, resume)")

    try:
        with open(OUT_FILE, "a", encoding="utf-8") as out:
            for url in to_process:
                if saved >= TARGET_DOCS:
                    break

                # несколько попыток на случай сбоев
                html = None
                for attempt in range(3):
                    try:
                        driver.get(url)
                        time.sleep(random.uniform(2.0, 3.5))
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(random.uniform(1.0, 2.0))
                        html = driver.page_source
                        break
                    except InvalidSessionIdException:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = setup_driver()
                    except WebDriverException:
                        time.sleep(2.0)

                if not html:
                    continue

                item = parse_article_html(html, url, MIN_CHARS)
                if not item:
                    continue

                out.write(json.dumps(item, ensure_ascii=False) + "\n")
                out.flush()

                saved += 1
                pbar.update(1)

    finally:
        pbar.close()
        try:
            driver.quit()
        except Exception:
            pass

    print(f"Итого сохранено документов: {saved} (см. {OUT_FILE})")


if __name__ == "__main__":
    main()
