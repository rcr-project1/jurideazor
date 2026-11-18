"""Character Error Rate (CER) between a hand-typed reference and an OCR output.

    .venv/bin/python src/eval/cer.py --ref eval/ar_truth/A1997003_p6.txt \
        --hyp-page data/raw/joradp/text_v2/ar/1997/A1997003.txt:6 --lang ar

CER = edit_distance(ref, hyp) / len(ref). 0.0 = identical, 1.0 = unusable.
"""

from __future__ import annotations

import argparse
import difflib
import re
import unicodedata
from collections import Counter
from pathlib import Path

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
NOISE = re.compile(r"[«»\"'’`|]")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(AR_DIGITS)
    text = DIACRITICS.sub("", text)
    text = text.replace("\u0640", "")
    text = NOISE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def edit_ops(ref: str, hyp: str) -> tuple[int, int, int, int]:
    n, m = len(ref), len(hyp)
    width = m + 1
    prev = list(range(width))
    trace = bytearray((n + 1) * width)
    for j in range(width):
        trace[j] = 2
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        trace[i * width] = 1
        for j in range(1, width):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            diag = prev[j - 1] + cost
            up = prev[j] + 1
            left = cur[j - 1] + 1
            best = min(diag, up, left)
            cur[j] = best
            trace[i * width + j] = 0 if best == diag else (1 if best == up else 2)
        prev = cur

    subs = ins = dels = 0
    i, j = n, m
    while i > 0 or j > 0:
        code = trace[i * width + j]
        if i > 0 and j > 0 and code == 0:
            subs += ref[i - 1] != hyp[j - 1]
            i, j = i - 1, j - 1
        elif i > 0 and (j == 0 or code == 1):
            dels += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return prev[m], subs, ins, dels


def digit_error(ref: str, hyp: str) -> tuple[int, int]:
    a = re.sub(r"\D", "", ref)
    b = re.sub(r"\D", "", hyp)
    if not a:
        return 0, 0
    return edit_ops(a, b)[0], len(a)


def year_stats(ref: str, hyp: str) -> tuple[int, int]:
    a = re.findall(r"\b\d{4}\b", ref)
    b = Counter(re.findall(r"\b\d{4}\b", hyp))
    good = 0
    for value in a:
        if b[value] > 0:
            b[value] -= 1
            good += 1
    return good, len(a)


def worst_blocks(ref: str, hyp: str, limit: int = 8) -> list[str]:
    matcher = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        left = ref[max(0, i1 - 25): i1]
        out.append(f"[{tag}] ...{left}[{ref[i1:i2]!r} -> {hyp[j1:j2]!r}]")
        if len(out) >= limit:
            break
    return out


def load_hyp(path: str) -> str:
    if ":" in path:
        file_part, page = path.rsplit(":", 1)
        if page.isdigit():
            pages = Path(file_part).read_text(encoding="utf-8").split("\n\f\n")
            return pages[int(page) - 1]
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True, help="hand-typed reference file")
    parser.add_argument("--hyp", help="OCR output file")
    parser.add_argument("--hyp-page", help="OCR output file:PAGE (1-based, separated by \\f)")
    parser.add_argument("--from-text", help="keep the hypothesis only from this marker (inclusive)")
    parser.add_argument("--to-text", help="keep the hypothesis only up to this marker (inclusive)")
    args = parser.parse_args()

    ref = normalize(Path(args.ref).read_text(encoding="utf-8"))
    hyp = normalize(load_hyp(args.hyp_page or args.hyp))
    if args.from_text:
        marker = normalize(args.from_text)
        start = hyp.find(marker)
        if start < 0:
            print(f"marker introuvable dans l'hypothèse : {args.from_text!r}")
            return 1
        hyp = hyp[start:]
    if args.to_text:
        marker = normalize(args.to_text)
        end = hyp.find(marker)
        if end < 0:
            print(f"marker introuvable dans l'hypothèse : {args.to_text!r}")
            return 1
        hyp = hyp[: end + len(marker)]
    if not ref:
        print("reference is empty")
        return 1

    dist, subs, ins, dels = edit_ops(ref, hyp)
    cerr, digits = digit_error(ref, hyp)
    print(f"ref chars: {len(ref):>5} | hyp chars: {len(hyp):>5}")
    print(f"CER = {dist / len(ref):.4f} ({dist} / {len(ref)})")
    print(f"substitutions: {subs} | deletions: {dels} | insertions: {ins}")
    if digits:
        print(f"chiffres: {cerr} / {digits} faux ({cerr / digits:.1%})")
    years_ok, years_total = year_stats(ref, hyp)
    if years_total:
        print(f"années/4-chiffres exactes: {years_ok} / {years_total} ({years_ok / years_total:.0%})")
    print("--- pires segments ---")
    for line in worst_blocks(ref, hyp):
        print(" ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
