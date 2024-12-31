import csv

with open("./dictionary/input/possessive.tsv", "r") as f:
    possessives: list[tuple[str, str, str]] = [
        (row[0], row[1], row[2]) for row in csv.reader(f, delimiter="\t")
    ]
possessives.pop(0)
