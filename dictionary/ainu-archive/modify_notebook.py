import json

ipynb_path = '/home/mkpoli/projects/Ainu/ainu-corpora-process/dictionary/ainu-archive/extract_words.ipynb'
with open(ipynb_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Find the cell that has "kayano_entries.loc" and remove it (as it's buggy and we'll replace it)
# Specifically, we want to pop the last two cells which are about kayano_entries
cells_to_keep = []
for cell in notebook['cells']:
    if cell.get('cell_type') == 'code':
        source_code = "".join(cell.get('source', []))
        if "kayano_entries" in source_code:
            continue
    cells_to_keep.append(cell)

notebook['cells'] = cells_to_keep

code_to_add = """# Automatically split citations into separate TSV files
import re

# Get unique citations
citations = set()
for d in cleaned_dictionary["definition"].dropna():
    m = re.search(r"（出典：(.*?)、", d)
    if m:
        citations.add(m.group(1))

# Dictionary of author -> file slug
author_slugs = {
    '萱野': 'kayano',
    '田村': 'tamura',
    '知里植物編': 'chiri-plants',
    '知里動物編': 'chiri-animals',
    '知里人間編I': 'chiri-human-1',
    '知里人間編II': 'chiri-human-2',
    '知里人間編III': 'chiri-human-3',
    '知里地名編': 'chiri-places',
}

from romajitable import to_roma

for citation in sorted(citations):
    # Filter the entries based on the citation
    # We use regex matching for the specific citation to avoid partial matches
    entries = cleaned_dictionary[
        cleaned_dictionary["definition"].str.contains(f"（出典：{citation}、", regex=False)
    ].copy()
    
    # Strip the citation from the definition string
    entries["definition"] = entries["definition"].apply(
        lambda x: re.sub(rf"（出典：{citation}、方言：.*?）", "", x)
    )
    
    # Check if we have a specific slug, otherwise generate one placeholder
    slug = author_slugs.get(citation, None)
    if not slug:
        # Fallback to pure citation string
        slug = citation
        
    filename = f"{slug}-entries.tsv"
    
    # Export to the output directory
    entries.to_csv(OUTPUT_DIR / filename, sep="\\t", index=False)
    print(f"Exported {len(entries)} entries to {filename}")
"""

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [line + "\n" for line in code_to_add.split('\n')[:-1]] + [code_to_add.split('\n')[-1]]
}

notebook['cells'].append(new_cell)

with open(ipynb_path, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=4, ensure_ascii=False)
