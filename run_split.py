import json
import pandas as pd
import re
from pathlib import Path

# Paths
OUTPUT_DIR = Path('/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/output/ainu-archive/')
dict_path = OUTPUT_DIR / 'cleaned-dictionary.tsv'

cleaned_dictionary = pd.read_csv(dict_path, sep='\t')

citations = set()
for d in cleaned_dictionary['definition'].dropna():
    m = re.search(r'（出典：(.*?)、', d)
    if m:
        citations.add(m.group(1))

print(f'Found citations: {citations}')

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

for citation in citations:
    entries = cleaned_dictionary[
        cleaned_dictionary['definition'].str.contains(f'（出典：{citation}、', regex=False)
    ].copy()
    
    entries['definition'] = entries['definition'].apply(
        lambda x: re.sub(rf'（出典：{citation}、方言：.*?）', '', x)
    )
    
    slug = author_slugs.get(citation, citation)
    filename = f'{slug}-entries.tsv'
    entries.to_csv(OUTPUT_DIR / filename, sep='\t', index=False)
    print(f'Exported {len(entries)} entries to {filename}')

print("Done.")
