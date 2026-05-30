"""Cross-reference our Latin-rule small-kana fix against Yasuoka's AinuOCR model.

Runs KoichiYasuoka/Qwen3.5-2B-AinuOCR (image-text-to-text, trained to read Ainu
katakana INCLUDING small kana) on cropped page images, and prints its output next
to our restored ain-kana for the same pages, so we can spot-check agreement.

Usage:  uv run --with torch --with 'transformers>=5.2.0' --with accelerate \
            --with pillow python -m dictionary.tamura_elpr_yasuoka_xref 18 67
"""

from __future__ import annotations

import sys
from pathlib import Path

from transformers import pipeline

ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT / "dictionary" / "output" / "tamura-elpr-ocr"
MODEL = "KoichiYasuoka/Qwen3.5-2B-AinuOCR"


def main() -> None:
    pages = [int(a) for a in sys.argv[1:]] or [18, 67]
    nlp = pipeline("image-text-to-text", MODEL, max_new_tokens=1024, device_map="auto")
    for p in pages:
        img = OCR_DIR / f"page-{p:03d}" / "images" / "cropped_page.png"
        if not img.exists():
            print(f"[page {p}] no image at {img}")
            continue
        doc = nlp(
            [{"role": "user", "content": [
                {"type": "image", "image": str(img)},
                {"type": "text", "text": "OCR Ainu sentences."},
            ]}]
        )
        text = doc[0]["generated_text"][-1]["content"]
        print(f"\n================ PAGE {p} — Yasuoka Qwen3.5-2B-AinuOCR ================")
        print(text)


if __name__ == "__main__":
    main()
