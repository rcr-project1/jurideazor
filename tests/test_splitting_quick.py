import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "split_articles",
    "src/structure/split_articles.py"
)
splitter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(splitter)

files = [
    ("fr", Path("data/processed/texts/1990/loi-90-11.txt")),
    ("fr", Path("data/processed/texts/1997/ordonnance-97-02.txt")),
]

for lang, path in files:
    articles = splitter.split_file(path, lang)

    numbered = [
        a for a in articles
        if a["article"] not in (None, "preambule")
    ]

    print(f"\nFile: {path.name}")
    print("Total records:", len(articles))
    print("Numbered articles:", len(numbered))
    print("Article numbers:", [a["article"] for a in numbered])

    assert articles, f"Empty result: {path}"
    assert all(a["content"].strip() for a in articles)

print("\nQuick test finished.")