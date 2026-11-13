"""structure: nettoyage + découpage de la loi 90-11 en articles.

Entrée  : data/raw/loi_90_11.txt
Sorties : data/processed/loi_90_11_clean.txt
          data/processed/articles.json
          data/processed/rapport_decoupage.txt   (à relire à la main)
Lancer depuis la racine du projet : python src/structure/split_loi_90_11.py
"""
import json
import re
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/loi_90_11.txt")
OUT = Path("data/processed")
SOURCE_URL = "https://www.wipo.int/wipolex/fr/legislation/details/14834"

# ---------- 1. lecture + bruit de pages ----------
text = RAW.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
lines = [l.strip() for l in text.split("\n")]
start = next(i for i, l in enumerate(lines) if l.startswith("LIVRE PREMIER"))
NOISE = re.compile(r"^(\d{1,3}|Relations de travaill?|Loi n° 90-11 du 21/04/1990)$")
pre = [l for l in lines[:start] if l and not NOISE.match(l)]
body = [l for l in lines[start:] if l and not NOISE.match(l)]

# ---------- 2. mots coupés en fin de ligne ----------
def tokens(s):
    return re.findall(r"[A-Za-zÀ-ÿ’']+", s.lower())

# mots "entiers" = ceux qui apparaissent au milieu d'une ligne (ni premier ni dernier mot,
# qui peuvent être des morceaux de mots coupés)
inline = Counter(t for l in body for t in tokens(l)[1:-1])
joined_words = []

def merge_lines(ls):
    """Colle les lignes ; recolle un mot coupé si le mot entier existe ailleurs."""
    out = ""
    for l in ls:
        if not out:
            out = l
            continue
        a = tokens(out)[-1:] or [""]
        b = tokens(l)[:1] or [""]
        a, b = a[0], b[0]
        if (a and b and out[-1].isalpha() and l[0].islower()
                and inline[a + b] >= 1 and inline[a] == 0):
            out += l
            joined_words.append(a + b)
        else:
            out += " " + l
    out = re.sub(r"\s+", " ", out).strip()
    return re.sub(r"\bl er\b", "1er", out)   # faute de scan : "l er" = "1er"

# ---------- 3. repérer les débuts d'article ----------
ART = re.compile(r"^Art(?:icle)?\.?\s*(\d+|ler|1er)(?:-(\d+))?\s*(bis|ter|quater)?\.?\s*([-–—])?\s*(.*)$", re.I)
RANK = {"": 0, "bis": 1, "ter": 2, "quater": 3}

def parse(l):
    m = ART.match(l)
    if not m:
        return None
    n = 1 if m.group(1).lower() in ("ler", "1er") else int(m.group(1))
    k = int(m.group(2)) if m.group(2) else RANK[(m.group(3) or "").lower()]
    label = str(n) + (f"-{m.group(2)}" if m.group(2) else "") + (f" {m.group(3).lower()}" if m.group(3) else "")
    spaced = bool(re.match(r"^Art(?:icle)?\.?\s*[\w-]+(?:\s+\w+\.?)?\s[-–—]\s", l))
    return (n, k), label, m.group(5), m.group(4) is not None, spaced

cands = []  # (index ligne, clé, label, texte restant, avec tiret, tiret espacé)
for i, l in enumerate(body):
    p = parse(l)
    if p and p[3]:
        cands.append((i, p[0], p[1], p[2], p[4]))

# plus longue suite croissante (les numéros hors ordre = erreurs de scan)
best, prev = [], [-1] * len(cands)
for j, c in enumerate(cands):
    best.append(1 + 0.5 * c[4])
    for i in range(j):
        if cands[i][1] < c[1] and best[i] + 1 + 0.5 * c[4] > best[j]:
            best[j], prev[j] = best[i] + 1 + 0.5 * c[4], i
j = max(range(len(cands)), key=lambda x: best[x])
accepted = []
while j != -1:
    accepted.append(j)
    j = prev[j]
accepted = [cands[j] for j in reversed(accepted)]
acc = {c[0]: c for c in accepted}
rejected = [(i, body[i]) for (i, *_rest) in cands if i not in acc]

# ---------- 4. découpage ----------
HEAD = re.compile(r"^(LIVRE|TITRE|Chapitre|Section)\s+([IVX\d]+|PREMIER|ler)\s*$", re.I)
ctx = {"livre": "", "titre": "", "chapitre": "", "section": ""}
articles, cur, markers_used, markers_dropped = [], None, [], []
want_title = None
acc_idx = sorted(acc)

def next_accepted_key(i):
    for a in acc_idx:
        if a > i:
            return acc[a][1]
    return None

for i, l in enumerate(body):
    h = HEAD.match(l)
    if h:
        kind = h.group(1).lower()
        ctx[kind] = l
        for lower in {"livre": ["titre", "chapitre", "section"], "titre": ["chapitre", "section"],
                      "chapitre": ["section"], "section": []}[kind]:
            ctx[lower] = ""
        want_title = kind
        continue
    if want_title and not ART.match(l):
        ctx[want_title] += " – " + l
        want_title = None
        continue
    want_title = None
    if i in acc:
        _, key, label, rest, _ = acc[i]
        if cur and cur["key"] == key:
            cur["lines"].append(rest)
        else:
            cur = {"key": key, "article": label, "lines": [rest], **{k: v for k, v in ctx.items() if k != "livre"}}
            articles.append(cur)
        continue
        
    p = parse(l)
    
    # --- FIX: Ignorer les faux débuts d'articles (ex: "Art. 9-" au milieu de l'Art 7) ---
    if p and i not in acc:
        continue
    # -------------------------------------------------------------------------------------

    if p and not p[3] and not p[2]:           # "Art. 5" seul sur la ligne
        if next_accepted_key(i) == p[0]:
            if not (cur and cur["key"] == p[0]):
                cur = {"key": p[0], "article": p[1], "lines": [], **{k: v for k, v in ctx.items() if k != "livre"}}
                articles.append(cur)
            markers_used.append(l)
        else:
            markers_dropped.append(f"ligne {i}: {l}")
        continue
    if cur:
        cur["lines"].append(l)

# ---------- 5. Constitution (extraits avant la loi) ----------
const = []
cc = None
for l in pre:
    p = parse(l)
    if p and p[3]:
        cc = {"article": p[1], "lines": [p[2]]}
        const.append(cc)
    elif cc:
        cc["lines"].append(l)

# ---------- 6. sorties ----------
def finish(a):
    a["texte"] = merge_lines(a.pop("lines"))
    a.pop("key", None)
    return a

records = []
for a in articles:
    a = finish(a)
    records.append({
        "texte_id": "loi-90-11", "article": a["article"], "titre": a["titre"],
        "chapitre": a["chapitre"], "section": a["section"], "contenu": a["texte"],
        "version": "1997", "date_debut": "1990-04-21", "date_fin": None, "source_url": SOURCE_URL,
    })
for c in const:
    records.append({
        "texte_id": "constitution-1996-extraits", "article": c["article"], "titre": "", "chapitre": "",
        "section": "", "contenu": merge_lines(c["lines"]), "version": "1996", "date_debut": None,
        "date_fin": None, "source_url": SOURCE_URL,
    })

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "articles.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "loi_90_11_clean.txt").write_text(
    "\n\n".join(f"Art. {r['article']} - {r['contenu']}" for r in records if r["texte_id"] == "loi-90-11"),
    encoding="utf-8")

loi = [r for r in records if r["texte_id"] == "loi-90-11"]
nums = sorted({int(re.match(r"\d+", r["article"]).group()) for r in loi})
short = [r["article"] for r in loi if len(r["contenu"]) < 60]
rare = Counter()
for r in loi:
    for t in tokens(r["contenu"]):
        if inline[t] == 0 and len(t) >= 3:
            rare[t] += 1

report = [
    f"Articles de la loi 90-11 trouvés : {len(loi)} (numéros distincts : {len(nums)})",
    f"Numéros manquants entre 1 et 158 : {sorted(set(range(1, 159)) - set(nums))}",
    f"Articles avec suffixe (bis, ter, -1...) : {[r['article'] for r in loi if not r['article'].isdigit()]}",
    f"Extraits de la Constitution : {[r['article'] for r in records if r['texte_id'].startswith('constitution')]}",
    f"Articles très courts (< 60 caractères) à relire : {short}",
    f"Mots coupés recollés automatiquement : {len(joined_words)}",
    "",
    "Débuts d'article ignorés (numéro hors ordre = erreur de scan, à vérifier) :",
    *[f"  ligne {i}: {t[:90]}" for i, t in rejected],
    "",
    "Lignes 'Art. N' seules ignorées :",
    *[f"  {m}" for m in markers_dropped],
    "",
    "Mots rares (apparaissent une seule fois, possibles mots coupés ou fautes de scan) :",
    "  " + ", ".join(sorted(rare)[:150]),
]
(OUT / "rapport_decoupage.txt").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report[:7]))
print("Fichiers écrits dans", OUT)