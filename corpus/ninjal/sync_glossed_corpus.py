from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.request import urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "corpus" / "output" / "ninjal"
STORY_INDEX_URL = (
    "https://ainu.ninjal.ac.jp/folklore/jp/stories_download/?page=1&start=0&limit=200"
)
STORY_BODY_URL = "https://ainu.ninjal.ac.jp/folklore/jp/story_body/{story_id}/"


def fetch_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_remote_story_ids() -> list[str]:
    data = fetch_json(STORY_INDEX_URL)
    return [row["story_id"] for row in data["data"] if row["story_id"] != "000"]


def get_local_story_ids() -> set[str]:
    return {path.stem for path in OUTPUT_DIR.glob("*.json")}


def sync_corpus(force: bool = False, sleep_seconds: float = 1.0) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    remote_story_ids = get_remote_story_ids()
    local_story_ids = get_local_story_ids()

    downloaded = 0
    skipped = 0
    for story_id in remote_story_ids:
        output_path = OUTPUT_DIR / f"{story_id}.json"
        if output_path.exists() and not force:
            skipped += 1
            continue

        data = fetch_json(STORY_BODY_URL.format(story_id=story_id))
        output_path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        downloaded += 1
        time.sleep(sleep_seconds)

    print(f"Remote stories: {len(remote_story_ids)}")
    print(f"Local stories before sync: {len(local_story_ids)}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Local stories after sync: {len(get_local_story_ids())}")
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incrementally sync the NINJAL glossed corpus."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download story files even if they already exist locally.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between downloads to avoid hammering the remote server.",
    )
    args = parser.parse_args()
    sync_corpus(force=args.force, sleep_seconds=args.sleep_seconds)


if __name__ == "__main__":
    main()
