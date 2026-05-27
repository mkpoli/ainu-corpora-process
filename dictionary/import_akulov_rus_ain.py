"""Scrape Akulov 2009 Russian-Ainu dictionary from rus_ain.academic.ru.

Source: https://rus_ain.academic.ru/
Author: А. Ю. Акулов, 2009 (Akulov, A. Yu.)

The site exposes one entry per numeric ID (1..1070). Each entry page contains
a Russian headword (`<dt class="term" lang="ru">`) and one Ainu translation
inside a `<dd class="descript" lang="ai">` block where the first `<div>` is
typically a clarifying Russian gloss / category and the second `<div>` is the
Ainu form. We preserve both as-is.
"""

from __future__ import annotations

import csv
import html
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2009_Akulov_Russian-Ainu-Dictionary"
RAW_DIR = FOLDER / "raw"
ENTRY_URL = "https://rus_ain.academic.ru/{id}/"
MAX_ID = 1070

# academic.ru's wildcard certificate doesn't cover underscored subdomains, so
# python's urllib stricter SNI check fails. Shell out to curl, which already
# returns the right content for this scrape.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ENTRY_RE = re.compile(
    r'<dt itemprop="term" class="term" lang="ru">(?P<term>.*?)</dt>\s*'
    r'<dd itemprop="definition" class="descript" lang="ai"><div>(?P<gloss>.*?)</div>\s*<div>(?P<ain>.*?)</div></dd>',
    re.DOTALL,
)
ENTRY_NO_GLOSS_RE = re.compile(
    r'<dt itemprop="term" class="term" lang="ru">(?P<term>.*?)</dt>\s*'
    r'<dd itemprop="definition" class="descript" lang="ai">(?P<ain>.*?)</dd>',
    re.DOTALL,
)


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(entry_id: int) -> str | None:
    url = ENTRY_URL.format(id=entry_id)
    raw_path = RAW_DIR / f"{entry_id}.html"
    if raw_path.exists() and raw_path.stat().st_size > 0:
        return raw_path.read_text(encoding="utf-8")
    for attempt in range(3):
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-sL",
                    "--max-time",
                    "20",
                    "-A",
                    USER_AGENT,
                    "-w",
                    "\n__HTTPSTATUS__%{http_code}\n",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=25,
            )
            output = result.stdout
            if not output:
                time.sleep(0.5 * (attempt + 1))
                continue
            # Strip the trailing status sentinel.
            m = re.search(r"\n__HTTPSTATUS__(\d+)\s*$", output)
            status = int(m.group(1)) if m else 0
            body = output[: m.start()] if m else output
            if status >= 300 and status < 400:
                return None
            if status != 200:
                time.sleep(0.5 * (attempt + 1))
                continue
            if "Страница не найдена" in body:
                return None
            raw_path.write_text(body, encoding="utf-8")
            return body
        except subprocess.TimeoutExpired:
            time.sleep(0.8 * (attempt + 1))
    return None


def parse(text: str) -> tuple[str, str, str] | None:
    match = ENTRY_RE.search(text)
    if match:
        return (clean(match["term"]), clean(match["gloss"]), clean(match["ain"]))
    match = ENTRY_NO_GLOSS_RE.search(text)
    if match:
        return (clean(match["term"]), "", clean(match["ain"]))
    return None


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    rows: dict[int, tuple[str, str, str]] = {}

    def worker(entry_id: int) -> tuple[int, tuple[str, str, str] | None]:
        text = fetch(entry_id)
        if text is None:
            return entry_id, None
        parsed = parse(text)
        return entry_id, parsed

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(worker, i): i for i in range(1, MAX_ID + 1)}
        done = 0
        for future in as_completed(futures):
            entry_id, parsed = future.result()
            done += 1
            if parsed is not None:
                rows[entry_id] = parsed
            if done % 50 == 0:
                print(f"  ...{done}/{MAX_ID} fetched, {len(rows)} parsed", flush=True)

    ordered = sorted(rows.items())
    out_path = FOLDER / "original.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "rus", "rus_gloss", "ain"])
        for entry_id, (term, gloss, ain) in ordered:
            writer.writerow([entry_id, term, gloss, ain])

    (FOLDER / "metadata.yaml").write_text(
        """type: dictionary
title: Русско-айнский словарь
title_en: Russian-Ainu Dictionary
author:
  en: Akulov, Alexander Yu.
  ru: Акулов, А. Ю.
year: 2009
url: https://rus_ain.academic.ru/
source: |
  Scraped from Academic.ru's hosted edition of Akulov's Russian-Ainu Dictionary
  (А. Ю. Акулов, Русско-айнский словарь, 2009). One entry per ID 1..1070.
  Each entry has a Russian headword and a single Ainu translation; an
  optional intermediate Russian "gloss" (extra context / category) is
  preserved verbatim where present.
columns:
  id: source entry ID on academic.ru
  rus: Russian headword
  rus_gloss: optional Russian clarifier / category appearing before the Ainu form
  ain: Ainu translation as printed
""",
        encoding="utf-8",
    )
    print(f"wrote {len(ordered)} Akulov Russian-Ainu entries to {out_path}")


if __name__ == "__main__":
    main()
