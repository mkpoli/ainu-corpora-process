"""Ingest the Ainu portion of the ASJP (Automated Similarity Judgment Program).

Source: https://github.com/lexibank/asjp (master/cldf)
License: CC BY 4.0 (ASJP database)

20 dialect points (Hokkaido + Sakhalin) × ~40 Swadesh meanings each, 818
form rows total. Useful as a comparative table — the broadest dialect-point
coverage of any open Ainu lexical resource.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

DICT_ROOT = Path("/home/mkpoli/projects/Ainu/ainu-dictionaries")
FOLDER = DICT_ROOT / "2020_ASJP_Ainu-Varieties"

FORMS_URL = "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/forms.csv"
PARAMS_URL = "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/parameters.csv"
LANGS_URL = "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/languages.csv"


def fetch_csv(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=120) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    forms = fetch_csv(FORMS_URL)
    params = {row["ID"]: row for row in fetch_csv(PARAMS_URL)}
    langs = {row["ID"]: row for row in fetch_csv(LANGS_URL)}

    rows: list[dict] = []
    for row in forms:
        lang_id = row["Language_ID"]
        if not lang_id.startswith("AINU_"):
            continue
        p = params.get(row["Parameter_ID"], {})
        lang = langs.get(lang_id, {})
        # ASJP Form is ASJP-coded (small phoneset). Value is the original.
        rows.append(
            {
                "variety": lang_id.removeprefix("AINU_").title(),
                "lemma": row["Value"],
                "asjp_form": row["Form"],
                "concept_en": p.get("Name", ""),
                "concept_id": row["Parameter_ID"],
                "latitude": lang.get("Latitude", ""),
                "longitude": lang.get("Longitude", ""),
                "glottocode": lang.get("Glottocode", ""),
            }
        )

    columns = ["variety", "lemma", "asjp_form", "concept_en", "concept_id", "latitude", "longitude", "glottocode"]
    tsv_path = FOLDER / "original.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})

    metadata = """type: comparative-wordlist
title: ASJP Ainu varieties (20 dialect points)
title_en: ASJP - Ainu varieties (Swadesh-style, 20 dialect points)
author:
  en: ASJP Consortium (Wichmann et al.)
year: 2020
dialect:
  name: 北海道・樺太
  paths:
    - 北海道
    - 樺太
parent:
  type: database
  title: Automated Similarity Judgment Program
  publisher: lexibank / clld
url: https://github.com/lexibank/asjp
license: CC BY 4.0
source: |
  20 Ainu varieties (Hokkaido + Sakhalin) with ~40 Swadesh meanings each:
    Hokkaido: Asahikawa, Bihoro, Hiratori, Horobetsu, Kushiro, Niikappu,
              Nukkibetsu, Obihiro, Oshamambe, Samani, Saru, Soya, Yakumo, Nayoro
    Sakhalin: Maoka, Nairo, Ochiho, Raichishka, Shiraura, Tarantomari
columns:
  variety:      dialect point (titlecased ASJP language code)
  lemma:        original Value field from the upstream source
  asjp_form:    ASJP small-phoneset transcription
  concept_en:   English Swadesh meaning
  concept_id:   ASJP parameter ID (Swadesh slot)
  latitude:     dialect-point latitude
  longitude:    dialect-point longitude
  glottocode:   Glottolog code (ainu1240)
"""
    (FOLDER / "metadata.yaml").write_text(metadata, encoding="utf-8")
    print(f"wrote {len(rows)} Ainu rows ({len({r['variety'] for r in rows})} varieties) to {tsv_path}")


if __name__ == "__main__":
    main()
