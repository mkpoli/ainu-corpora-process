import json
from pathlib import Path

POS_PATH = Path(__file__).parent / "combined_part_of_speech.json"

with open(POS_PATH, "r") as f:
    combined_pos = json.load(f)
