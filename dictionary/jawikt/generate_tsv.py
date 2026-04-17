import json
import csv
from pathlib import Path

# Paths
INPUT_JSON = Path('/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/output/wiktionary_ainu_glosses.json')
OUTPUT_TSV = Path('/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/output/wiktionary-entries.tsv')

POS_JA = {
    "noun": "名詞",
    "verb": "動詞",
    "adv": "副詞",
    "adnom": "連体詞",
    "auxverb": "助動詞",
    "colloc": "成句",
    "conj": "接続詞",
    "interj": "間投詞",
    "num": "数詞",
    "parti": "助詞",
    "postpadv": "後置副詞",
    "prefix": "接頭辞",
    "pron": "代名詞",
    "pronoun": "代名詞",
    "rel": "関係詞",
    "suffix": "接尾辞",
    "root": "語根",
    "determiner": "限定詞",
}

def main():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        gloss_dict = json.load(f)

    entries = []
    for key, data in gloss_dict.items():
        lemma = data.get("lemma", key)
        pos = data.get("pos", "")
        glosses = data.get("glosses", [])
        
        # Map POS to Japanese
        pos_ja = POS_JA.get(pos, pos) if pos else ""
        
        definition = "、".join(glosses)
        
        entries.append([lemma, pos_ja, definition])
        
    print(f"Loaded {len(entries)} entries from Wiktionary")

    with open(OUTPUT_TSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['lemma', 'pos', 'definition'])  # Header
        for entry in entries:
            writer.writerow(entry)

    print(f"Successfully generated TSV at {OUTPUT_TSV}")

if __name__ == "__main__":
    main()
