import csv
import re
from pathlib import Path

# Paths
OUTPUT_DIR = Path('/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/output/ainu-archive/')
dict_path = OUTPUT_DIR / 'cleaned-dictionary.tsv'

# Read all entries
entries = []
with open(dict_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    headers = next(reader)
    for row in reader:
        if len(row) >= 2:
            entries.append({"lemma": row[0], "definition": row[1]})

# Extract citations
citations = set()
for entry in entries:
    m = re.search(r'（出典：(.*?)、', entry["definition"])
    if m:
        citations.add(m.group(1))

print(f"Found citations: {citations}", flush=True)

author_slugs = {
    '萱野': 'kayano',
    '田村': 'tamura',
    '知里植物編': 'chiri-plants',
    '知里動物編': 'chiri-animals',
    '知里人間編I': 'chiri-human-1',
    '知里人間編II': 'chiri-human-2',
    '知里人間編III': 'chiri-human-3',
    '知里人間編Ⅰ': 'chiri-human-1',
    '知里人間編Ⅱ': 'chiri-human-2',
    '知里人間編Ⅲ': 'chiri-human-3',
    '知里地名編': 'chiri-places',
}

# Group and save
for citation in citations:
    citation_entries = []
    
    # Filter and clean
    for entry in entries:
        if f"（出典：{citation}、" in entry["definition"]:
            # Clean
            clean_def = re.sub(rf"（出典：{citation}、方言：.*?）$", "", entry["definition"])
            citation_entries.append([entry["lemma"], clean_def])
            
    slug = author_slugs.get(citation, citation)
    filename = f"{slug}-entries.tsv"
    
    with open(OUTPUT_DIR / filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(headers)
        for row in citation_entries:
            writer.writerow(row)
            
    print(f"Exported {len(citation_entries)} entries to {filename}", flush=True)

print("Done.", flush=True)
