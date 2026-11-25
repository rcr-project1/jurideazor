#!/usr/bin/env python3
"""OCR vs transcription manuelle : WER, CER, erreurs numériques.
Usage: python eval/ocr_eval.py eval/pages.csv [sortie.md]
pages.csv : doc,page,gold,ocr   (ocr = fichier texte ; si présence de \\f, on prend la page N)
"""
import csv, re, sys, unicodedata, difflib
from pathlib import Path

def norm(t):
    t = unicodedata.normalize("NFKC", t)
    t = t.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"',
                                   "—": "-", "–": "-", "−": "-"}))
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)      # césure fin de ligne
    t = re.sub(r"(?<=\w)-(?=\w)", "", t)               # césure écrite sur une ligne : indéter-minée
    return re.sub(r"\s+", " ", t).strip()

HEADER = re.compile(r"JOURNAL OFFICIEL|ALGERIENNE|^\W*\d{3}\W*$|^\W*25 [Aa]vril 1990\W*$")
def strip_headers(t):
    return "\n".join(l for l in t.splitlines() if not HEADER.search(l.strip()))

def words(t):  return re.findall(r"[\w']+", norm(t))
def nums(ws):  return [w for w in ws if re.search(r"\d", w)]
def arts(t):   return re.findall(r"Art\.?\s*(\d+)", norm(t))
def mixed(w):
    return len({unicodedata.name(c, "?").split()[0] for c in w if c.isalpha()}) > 1

def diff(g, o):
    sm = difflib.SequenceMatcher(None, g, o, autojunk=False)
    S = D = I = 0
    errs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        a, b = i2 - i1, j2 - j1
        S += min(a, b); D += max(a - b, 0); I += max(b - a, 0)
        errs.append((" ".join(g[max(0, i1 - 3):i1]), " ".join(g[i1:i2]) or "∅",
                     " ".join(o[j1:j2]) or "∅", tag))
    return S, D, I, errs

def main(csv_path, out="eval/ocr_quality_check.md"):
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    T = dict(w=0, we=0, c=0, ce=0, n=0, ne=0, a=0, ae=0)
    summary, details = [], []
    for r in rows:
        gold = Path(r["gold"]).read_text(encoding="utf-8")
        ocr = Path(r["ocr"]).read_text(encoding="utf-8").strip("\f\n ")
        if "\f" in ocr:
            ocr = ocr.split("\f")[int(r["page"]) - 1]
        gold, ocr = strip_headers(gold), strip_headers(ocr)
        g, o = words(gold), words(ocr)
        S, D, I, errs = diff(g, o)
        gc, oc = list(norm(gold)), list(norm(ocr))
        cS, cD, cI, _ = diff(gc, oc)
        nS, nD, nI, nerrs = diff(nums(g), nums(o))
        aS, aD, aI, _ = diff(arts(gold), arts(ocr))
        we, ce, ne, ae = S + D + I, cS + cD + cI, nS + nD + nI, aS + aD + aI
        T["w"] += len(g); T["we"] += we; T["c"] += len(gc); T["ce"] += ce
        T["n"] += len(nums(g)); T["ne"] += ne; T["a"] += len(arts(gold)); T["ae"] += ae
        summary.append(f"| {r['doc']} | {r['page']} | {len(g)} | {we} | {we/len(g):.2%} | "
                       f"{ce/len(gc):.2%} | {ne}/{len(nums(g))} | {ae}/{len(arts(gold))} |")
        bad = [w for w in o if mixed(w)]
        details.append(f"\n## {r['doc']} — page {r['page']}\n"
                       f"**Erreurs mots** (contexte | gold → OCR)\n" +
                       "\n".join(f"- `{c}` | **{a}** → **{b}** ({t})" for c, a, b, t in errs) +
                       f"\n\n**Erreurs numériques** : " +
                       (", ".join(f"{a}→{b}" for _, a, b, _ in nerrs) or "aucune") +
                       f"\n\n**Mots à scripts mélangés (homoglyphes)** : {bad or 'aucun'}\n")
    md = ["# OCR quality check — JORADP\n",
          "Gold = transcription manuelle ; tokens = mots `[\\w']+` après normalisation ; "
          "erreurs = S+D+I (difflib).\n",
          "| Fichier | Page | Mots gold | Mots faux | WER | CER | Chiffres faux | N° d'articles faux |",
          "|---|---|---|---|---|---|---|---|", *summary,
          f"| **TOTAL** | | {T['w']} | {T['we']} | **{T['we']/T['w']:.2%}** | "
          f"**{T['ce']/T['c']:.2%}** | **{T['ne']}/{T['n']}** | **{T['ae']}/{T['a']}** |",
          *details]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(md), encoding="utf-8")
    print("écrit :", out)

if __name__ == "__main__":
    main(*sys.argv[1:])