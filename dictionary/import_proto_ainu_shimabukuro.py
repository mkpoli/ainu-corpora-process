"""Parse Shimabukuro's Proto-Ainu Swadesh PDF (after Vovin 1993).

Source PDF: https://w3.u-ryukyu.ac.jp/tonga/ling/_userdata/proto-ainu.pdf
Author: Moriyo Shimabukuro (2015), University of the Ryukyus
Data source: Vovin, Alexander (1993) A Reconstruction of Proto-Ainu.
             Leiden / New York / Köln: E.J. Brill.

The PDF is a Swadesh-style table with 381 numbered concepts. For each
concept it gives English gloss, Japanese gloss, and zero, one, or
several Proto-Ainu reconstructions (marked with *, with tones LH/HL/etc).

Layout (pdftotext -layout):

    1         adult             大人
    2       afternoon           午後
                                       *Opit(=)ta,
    3           all             全て
                                       *Opir=ta LH-L
                                       *tE(=)k L "hand", "arm",
    4          arm              腕
                                       *amurnin LHL 'forearm'

We identify entry rows by a leading digit + word + Japanese, then keep
accumulating reconstruction-only lines until the next numbered row.
"""

from __future__ import annotations

import re
import subprocess
import csv
import html
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2015_Shimabukuro_Proto-Ainu-Swadesh"
PDF_URL = "https://w3.u-ryukyu.ac.jp/tonga/ling/_userdata/proto-ainu.pdf"

# Column X-coordinate boundaries from observed bbox geometry in the PDF.
# (Page width 595pt; left ~67, English ~115, Japanese ~200, Recon ~260+.)
X_NUM_MAX = 85.0  # entry numbers fit in xMin ~65-76; English starts at ~97
X_EN_MAX = 180.0  # English column extends to ~155 max
X_JA_MAX = 245.0  # Japanese column ~195-230
# Y-tolerance for grouping a reconstruction with an entry header: each entry's
# "vertical slot" is about 18pt wide (the row pitch is 18pt). The first recon
# of a multi-recon entry appears ~9pt *above* the entry header line.
RECON_Y_TOLERANCE = 14.0
# Pattern to pull <word ... yMin="..." xMin="...">TEXT</word> tuples from
# pdftotext -bbox-layout XML.
WORD_RE = re.compile(
    r'<word\s+xMin="(?P<xmin>[\d.]+)"\s+yMin="(?P<ymin>[\d.]+)"\s+xMax="(?P<xmax>[\d.]+)"\s+yMax="(?P<ymax>[\d.]+)">(?P<text>[^<]+)</word>'
)


def fetch_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with urllib.request.urlopen(PDF_URL, timeout=120) as response, path.open("wb") as out:
        out.write(response.read())


def pdf_to_bbox_xml(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf_path), "-"],
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


def parse_bbox(xml: str) -> list[dict[str, str]]:
    """Reconstruct each row by Y-coordinate clustering within each page.

    Each entry has a row-anchor Y (the entry-number line). Reconstructions for
    that row are the * tokens whose yMin is within +/-tolerance of the anchor
    plus the row-pitch slots above and below (since multi-recon cells stack
    around the header). We must respect page boundaries since the PDF resets Y
    on each page.
    """
    # Split XML by page so Y coordinates only group within a page.
    pages = re.split(r"<page\b[^>]*>", xml)[1:]
    words: list[tuple[int, float, float, str]] = []
    for page_idx, page_xml in enumerate(pages):
        for m in WORD_RE.finditer(page_xml):
            words.append(
                (
                    page_idx,
                    float(m["ymin"]),
                    float(m["xmin"]),
                    html.unescape(m["text"]),
                )
            )

    # Cluster words into rows by Y proximity within each page. Row pitch is
    # ~18pt; the Japanese gloss is rendered ~3pt below the Latin baseline so
    # we want a tolerance of ~6pt to capture both as one row.
    Y_TOLERANCE = 7.0
    rows_by_y: dict[tuple[int, float], list[tuple[float, str]]] = {}
    by_page_y: dict[int, list[tuple[float, float, str]]] = {}
    for page, ymin, xmin, txt in words:
        by_page_y.setdefault(page, []).append((ymin, xmin, txt))
    for page, lst in by_page_y.items():
        lst.sort()
        cluster_y = None
        for ymin, xmin, txt in lst:
            if cluster_y is None or ymin - cluster_y > Y_TOLERANCE:
                cluster_y = ymin
            rows_by_y.setdefault((page, cluster_y), []).append((xmin, txt))

    # Build row records: (page, y_anchor) -> {num, en, ja, recons}
    rows: list[dict] = []
    for key in sorted(rows_by_y):
        page, y = key
        row = sorted(rows_by_y[key])
        # row is a list of (xmin, text) sorted by xmin
        en_parts: list[str] = []
        ja_parts: list[str] = []
        recon_parts: list[str] = []
        num = ""
        for xmin, txt in row:
            # Reconstructions always start with *; classify by content first.
            if txt.startswith("*") or any(p.startswith("*") for p in recon_parts):
                recon_parts.append(txt)
                continue
            # Classify by character set: any non-ASCII char => Japanese gloss.
            is_japanese = any(ord(c) > 0x7F for c in txt)
            if is_japanese:
                ja_parts.append(txt)
            elif xmin < X_NUM_MAX:
                num = txt
            else:
                en_parts.append(txt)
        rows.append(
            {
                "page": page,
                "y": y,
                "num": num,
                "en": " ".join(en_parts).strip(),
                "ja": " ".join(ja_parts).strip(),
                "recon": " ".join(recon_parts).strip(),
            }
        )

    # Separate header rows (those with a numeric `num`) from pure-recon rows.
    header_rows: list[dict] = []
    recon_only_rows: list[dict] = []
    for row in rows:
        if row["num"].isdigit():
            header_rows.append(row)
        elif row["recon"]:
            recon_only_rows.append(row)

    # Assign each pure-recon row to its nearest header on the same page.
    by_page: dict[int, list[dict]] = {}
    for h in header_rows:
        by_page.setdefault(h["page"], []).append(h)
    for rec in recon_only_rows:
        page_headers = by_page.get(rec["page"], [])
        if not page_headers:
            continue
        best = min(page_headers, key=lambda h: abs(rec["y"] - h["y"]))
        extra = rec["recon"]
        if best.get("recon"):
            best["recon"] = best["recon"] + " " + extra
        else:
            best["recon"] = extra

    results: list[dict[str, str]] = []
    for h in header_rows:
        # The header row itself may already have an inline recon (case: short
        # Japanese gloss + 1 recon on same line).
        results.append(
            {
                "num": h["num"],
                "concept_en": h["en"],
                "concept_ja": h["ja"],
                "reconstructions": h.get("recon", "").strip(),
            }
        )
    # Sort by num.
    results.sort(key=lambda r: int(r["num"]))
    return results


def parse(text: str) -> list[dict[str, str]]:
    """Parse the layout-text output.

    Subtlety: when an entry has multiple reconstructions and they wrap inside
    the right-hand cell, pdftotext -layout outputs the *first* reconstruction
    line on the row's top whitespace and the entry header on a lower line.
    So a recon line that appears immediately *before* an entry header line
    belongs to that header, not to the previous one. We therefore collect
    pending recons and flush them onto the entry header when it arrives.
    """
    rows: list[dict[str, list[str] | str]] = []
    pending_recons: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if "Data source" in line or "Vovin, Alexander" in line:
            continue
        m_head = ENTRY_HEAD_RE.match(line)
        if m_head:
            entry = {
                "num": m_head["num"],
                "en": m_head["en"].strip(),
                "ja": m_head["ja"].strip(),
                "recon": list(pending_recons),
            }
            pending_recons.clear()
            rows.append(entry)
            continue
        m_recon = RECON_RE.match(line)
        if m_recon:
            pending_recons.append(m_recon["recon"])
            continue
        # Lines with a leading * but less whitespace than RECON_RE expects
        # (rare) — append to the pending queue.
        if line.strip().startswith("*"):
            pending_recons.append(line.strip())

    # Any pending recons at end-of-text belong to the last entry.
    if rows and pending_recons:
        rows[-1]["recon"].extend(pending_recons)  # type: ignore[arg-type]

    return [
        {
            "num": str(r["num"]),
            "concept_en": str(r["en"]),
            "concept_ja": str(r["ja"]),
            "reconstructions": "; ".join(r["recon"]),  # type: ignore[arg-type]
        }
        for r in rows
    ]


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    pdf_path = FOLDER / "proto-ainu.pdf"
    fetch_pdf(pdf_path)
    xml = pdf_to_bbox_xml(pdf_path)
    rows = parse_bbox(xml)

    columns = ["num", "concept_en", "concept_ja", "reconstructions"]
    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})

    metadata = """type: comparative-wordlist
title: Proto-Ainu Swadesh (after Vovin 1993)
title_en: Proto-Ainu Swadesh list (Shimabukuro 2015, after Vovin 1993)
author:
  en: Shimabukuro, Moriyo
  ja: 島袋, 盛世
year: 2015
dialect:
  name: Proto-Ainu
  path: 祖アイヌ
parent:
  type: pdf
  title: 'Proto-Ainu (Vovin 1993)'
  publisher: University of the Ryukyus
url: https://w3.u-ryukyu.ac.jp/tonga/ling/_userdata/proto-ainu.pdf
license: research / educational use
source: |
  PDF compiled by Moriyo Shimabukuro, U. of the Ryukyus, 2015. 381 Swadesh
  meanings with English + Japanese glosses and zero-or-more Proto-Ainu
  reconstructions taken from Vovin, Alexander (1993) A Reconstruction of
  Proto-Ainu. Leiden / New York / Köln: E.J. Brill.
  Reconstructions are marked with `*` and carry suprasegmental tone
  annotations (L = Low, H = High). Where the source PDF lists multiple
  reconstructions for one concept, they are joined with `; ` in the
  `reconstructions` column.
columns:
  num:              row number in Shimabukuro's table (1-381)
  concept_en:       English gloss
  concept_ja:       Japanese gloss
  reconstructions:  one or more Proto-Ainu reconstructions, separated by `; `
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(
        f"wrote {len(rows)} Proto-Ainu Swadesh entries to {tsv_path} "
        f"({sum(1 for r in rows if r['reconstructions'])} with reconstructions)"
    )


if __name__ == "__main__":
    main()
