"""Clean the French OCR output without touching numbers.

Design rule: this module may remove *layout*, never *content*. No digit, no
comma inside a number, no date is modified. Every removed line is counted AND
written to a side file (--dropped) so that the report can prove what was
thrown away.

What changed compared with the first version (see the review notes):

  * Page headers ("JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE N° 20",
    "13 avril 1994", "3 Ramadhan 1417") are only removed from the FIRST lines of
    a page. Before, the patterns ran on every line of every page and removed
    real text: a body line that starts with "Journal officiel de la République
    algérienne démocratique ..." (the publication formula) or that is only
    "correspondant au 31 décembre 1996" (the date of a title) was thrown away.
  * Masthead patterns (subscription block, "33è ANNÉE") only run on page 1.
  * A hyphen at the end of a line is removed only when the glued word exists
    elsewhere in the corpus (or the hyphenated word does). Otherwise the line
    is left as the OCR gave it. Before, two unrelated columns were glued
    ("chômage-" + "instituant" -> "chômageinstituant").
  * "œ" and "æ" are kept (they were rewritten to "oe" / "ae").
  * Dead code removed (the first `key = ...` line was overwritten at once).

Usage:
    python src/structure/clean_text.py
    python src/structure/clean_text.py --in data/raw/joradp/text_v2/fr \
        --out data/processed/text_clean/fr \
        --report data/processed/clean_report.csv \
        --dropped data/processed/dropped_lines_fr.txt
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

PAGE_SEP = "\n\f\n"

# How many lines (that contain a letter or a digit) at the top of a page may be
# a running header. Headers on two-column pages are split in 2-3 fragments.
TOP_LINES = 5
# Page 1 carries the masthead (subscription prices, "33è ANNÉE", ...).
MASTHEAD_LINES = 12

# --- masthead: page 1 only -------------------------------------------------
MASTHEAD_PATTERNS = [
    ("masthead", re.compile(r"^\d{1,2}\s*[èe]re?\s*ann[ée]e\s*$", re.I)),
    ("masthead", re.compile(r"^(direction\s+et\s+r[ée]daction|secr[ée]tariat\s+g[ée]n[ée]ral)\s*:?$", re.I)),
    ("masthead", re.compile(r"^(abonnement|etranger|[ée]tranger|du\s+gouvernement|tarif\s+des\s+insertions)\s*:?$", re.I)),
    # date line of the masthead, e.g. "correspondant au 13 avril 1994"
    ("masthead_date", re.compile(r"^correspondant\s+au\s+\d{1,2}(?:er)?\s+\w+\s+\d{4}\s*$", re.I)),
]

# --- running header: first lines of any page ---------------------------------
GREG_MONTHS = r"janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre"
HIJRI_WORDS = (
    r"moharram|safar|rabie|aouel|ethani|joumada|oula|ethania|rajab|cha[âa]bane|ramadhan|chaoual|dhou|kaada|hidja"
)
MONTH_WORD = re.compile(rf"(?i)(?:{GREG_MONTHS}|{HIJRI_WORDS})")
# "25 décembre 1991", "13. avril: 1994", "2 Dhou El Kaada 1414", "12: janvier 1997",
# optionally with a page number before or after ("25 décembre 1991 2193").
DATE_ONLY = re.compile(
    r"^[\W_]{0,4}(?:\d{1,4}\s+)?[\dOIl]{1,3}[\W_]{0,3}\s*(?P<mid>[A-Za-zÀ-ÿ'’ ]{3,28}?)[\W_]{0,3}\s*(?:1[34]|19)\d\d[\W_]{0,3}(?:\s+\d{1,4})?[\W_]{0,3}$"
)
# The tail of a sentence that continues with a date on the next line.
DATE_CONTINUES = re.compile(r"(?i)(?:correspondant(?:\s+au)?|\bau|\bdu|\ble|\bdate)\W*$")
# "JOURNAL OFFICIEL DE LA REPUBLIQUE ALGERIENNE N° 20" in all its OCR variants
# ("NAL OFFICIEL DE LA REPUBLIQE", "JOURNAL GFFICIEL ...", "18 JOURNAL OFFICIEL ...").
JO_HEADER = re.compile(r"(?i)[ogc]ff?icie[l1].{0,12}r[ée]publi")
JO_TAIL = re.compile(r"(?i)^[\W\d]*(?:publique\s+)?alg[ée]rienne\s+n[°o]?\s*\d*\W*$")
LONE_NUMBER = re.compile(r"(?i)^n[°o]\s*\d{1,3}\W{0,2}$")

DIGIT_ONLY = re.compile(r"^[\d.,\s]+$")
COMPOUND_PREFIXES = {
    "sous", "contre", "anti", "auto", "co", "pre", "post", "non", "semi",
    "vice", "ex", "neo", "ultra", "supra", "inter", "intra", "multi", "mono",
    "bi", "tri", "hyper", "hypo", "macro", "micro", "mini", "tele", "demi",
    "mi", "quasi", "pro", "trans", "extra", "archi", "arriere", "avant",
}
LEADERS = re.compile(r"\.{5,}")
ORPHAN = re.compile(r"^[|:—–\-.,;·/\\_=+*~^<>()\[\]{}\s]*$")
# word- ⏎ word : the right-hand word is captured so we can decide with evidence
HYPHEN_BREAK = re.compile(r"(?P<l>[^\W\d_]+)-[ \t]*\n(?P<r>[^\W\d_]+)", re.UNICODE)
ART_COMMA = re.compile(r"\bArt,")
WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
HYPHENATED = re.compile(r"[^\W\d_]{2,}-[^\W\d_]{2,}", re.UNICODE)


def normalize_chars(text: str) -> str:
    """NFKC + remove soft hyphens. "œ" / "æ" are NOT rewritten any more."""
    text = unicodedata.normalize("NFKC", text)
    return text.replace("­", "")


def nfkc_changes(text: str) -> int:
    """How many characters NFKC rewrites (e.g. "²" -> "2", "º" -> "o", "…" -> "...")."""
    cache: dict[str, bool] = {}
    n = 0
    for ch in text:
        if ord(ch) < 128:
            continue
        if ch not in cache:
            cache[ch] = unicodedata.normalize("NFKC", ch) != ch
        n += cache[ch]
    return n


def build_vocab(texts: list[str]) -> tuple[Counter, Counter]:
    """Words seen in the corpus, split in (plain words, hyphenated words).

    Built on text BEFORE the line-end hyphens are touched, so a word that was cut
    by the OCR at a line end only exists here if it also appears whole somewhere
    else. That is the evidence used to decide how to join a cut word."""
    plain: Counter = Counter()
    hyph: Counter = Counter()
    for t in texts:
        t = normalize_chars(t)
        plain.update(w.lower() for w in WORD.findall(t))
        hyph.update(w.lower() for w in HYPHENATED.findall(t))
    return plain, hyph


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def _upper_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0.0


def header_rule(stripped: str, prev_tail: str) -> str | None:
    """Rule name if `stripped` (a line from the top of a page) is a running header."""
    if len(stripped) <= 95 and JO_HEADER.search(stripped) and "démocratique" not in stripped.lower():
        # a real header is printed in capitals; the publication formula in body
        # text ("Journal officiel de la République algérienne démocratique") is not
        if _upper_ratio(stripped) >= 0.6:
            return "header_jo"
    if len(stripped) <= 40 and JO_TAIL.match(stripped) and _upper_ratio(stripped) >= 0.6:
        return "header_jo_tail"
    if LONE_NUMBER.match(stripped):
        return "header_number"
    m = DATE_ONLY.match(stripped)
    if m and MONTH_WORD.search(m.group("mid")):
        # "... correspondant au" / "11 janvier 1997" cut by a page break: real text
        if DATE_CONTINUES.search(prev_tail):
            return None
        return "header_date"
    return None


def clean_french(
    text: str,
    vocab: tuple[Counter, Counter] | None = None,
    dropped: list[tuple[int, int, str, str]] | None = None,
    top_lines: int = TOP_LINES,
) -> tuple[str, dict[str, int]]:
    """Clean one issue. `dropped` receives (page, line_no, rule, text) for every removed line."""
    counters = {
        "header_dropped": 0,
        "header_top_dropped": 0,
        "masthead_dropped": 0,
        "digit_lines_kept": 0,
        "hyphen_kept": 0,
        "leaders_dropped": 0,
        "orphan_dropped": 0,
        "hyphen_joined": 0,
        "hyphen_unresolved": 0,
        "art_commas_fixed": 0,
        "nfkc_changed": 0,
        "oe_ae_kept": 0,
    }
    counters["nfkc_changed"] = nfkc_changes(text)
    text = normalize_chars(text)
    counters["oe_ae_kept"] = sum(text.count(c) for c in "œŒæÆ")
    counters["art_commas_fixed"] = len(ART_COMMA.findall(text))
    text = ART_COMMA.sub("Art.", text)

    plain, hyph = vocab if vocab is not None else build_vocab([text])

    def join_word(m: re.Match) -> str:
        left, right = m.group("l"), m.group("r")
        l, r = left.lower(), right.lower()
        joined, hyphenated = l + r, f"{l}-{r}"
        n_join, n_hyph = plain.get(joined, 0), hyph.get(hyphenated, 0)
        if n_join or n_hyph:
            if n_hyph >= n_join:
                counters["hyphen_kept"] += 1
                return f"{left}-{right}"
            counters["hyphen_joined"] += 1
            return left + right
        if _fold(left) in COMPOUND_PREFIXES:
            counters["hyphen_kept"] += 1
            return f"{left}-{right}"
        # no evidence: leave the OCR output exactly as it is
        counters["hyphen_unresolved"] += 1
        return m.group(0)

    text = HYPHEN_BREAK.sub(join_word, text)

    out_pages = []
    prev_tail = ""  # last non-empty line of the previous page
    for pno, page in enumerate(text.split(PAGE_SEP), start=1):
        kept = []
        k = 0  # rank of the line among the lines that carry a letter or a digit
        for lno, line in enumerate(page.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                kept.append("")
                continue
            has_alnum = bool(re.search(r"\w", stripped))
            rank = k
            k += has_alnum

            rule = None
            if pno == 1 and rank < MASTHEAD_LINES:
                for name, p in MASTHEAD_PATTERNS:
                    if p.match(stripped):
                        rule = name
                        counters["masthead_dropped"] += 1
                        break
            if rule is None and has_alnum and rank < top_lines:
                rule = header_rule(stripped, prev_tail)
                if rule:
                    counters["header_top_dropped"] += 1
            if rule:
                counters["header_dropped"] += 1
                if dropped is not None:
                    dropped.append((pno, lno, rule, stripped))
                continue

            if DIGIT_ONLY.match(stripped):
                counters["digit_lines_kept"] += 1
                kept.append(stripped)
                prev_tail = stripped
                continue
            if LEADERS.search(stripped):
                counters["leaders_dropped"] += 1
                if dropped is not None:
                    dropped.append((pno, lno, "leaders", stripped))
                continue
            if ORPHAN.match(stripped) and not re.search(r"\w", stripped):
                counters["orphan_dropped"] += 1
                if dropped is not None:
                    dropped.append((pno, lno, "orphan", stripped))
                continue
            kept.append(stripped)
            prev_tail = stripped
        page_text = "\n".join(kept)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text).strip("\n")
        out_pages.append(page_text)

    cleaned = PAGE_SEP.join(p for p in out_pages if p)
    counters["pages_kept"] = len([p for p in out_pages if p])
    counters["chars_before"] = len(text)
    counters["chars_after"] = len(cleaned)
    return cleaned, counters


def iter_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*/*.txt"))
    return [path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/raw/joradp/text_v2/fr")
    ap.add_argument("--out", default="data/processed/text_clean/fr")
    ap.add_argument("--report", default="data/processed/clean_report.csv")
    ap.add_argument("--dropped", default="data/processed/dropped_lines_fr.txt")
    ap.add_argument("--top-lines", type=int, default=TOP_LINES, help="lines at the top of a page checked as header")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = iter_inputs(src)
    if not files:
        print(f"no .txt under {src}")
        return 1

    raw = {f: f.read_text(encoding="utf-8") for f in files}
    vocab = build_vocab(list(raw.values()))  # evidence for joining cut words

    rows = []
    dropped_all: list[str] = []
    for f in files:
        dropped: list[tuple[int, int, str, str]] = []
        cleaned, c = clean_french(raw[f], vocab, dropped, args.top_lines)
        target = out / f.parent.name / f.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(cleaned, encoding="utf-8")
        rows.append({"file": f.name, **c})
        dropped_all += [f"{f.name}\t{p}\t{ln}\t{rule}\t{txt}" for p, ln, rule, txt in dropped]
        ratio = c["chars_after"] / max(1, c["chars_before"])
        print(
            f"{f.name}: {c['pages_kept']} pages, {c['chars_before']} -> {c['chars_after']} "
            f"({ratio:.3f}) | en-têtes haut de page {c['header_top_dropped']}, bandeau p.1 {c['masthead_dropped']}, "
            f"points de suite {c['leaders_dropped']}, lignes ponctuation {c['orphan_dropped']}, "
            f"césures jointes {c['hyphen_joined']} / gardées {c['hyphen_kept']} / non résolues {c['hyphen_unresolved']}, "
            f"lignes chiffres gardées {c['digit_lines_kept']}, Art, {c['art_commas_fixed']}, "
            f"NFKC {c['nfkc_changed']}, œ/æ gardés {c['oe_ae_kept']}"
        )

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    dropped_path = Path(args.dropped)
    dropped_path.parent.mkdir(parents=True, exist_ok=True)
    dropped_path.write_text("file\tpage\tline\trule\ttext\n" + "\n".join(dropped_all) + "\n", encoding="utf-8")

    print(f"\n-> {out} ({len(rows)} fichiers)\n-> {report}\n-> {dropped_path} ({len(dropped_all)} lignes supprimées)")
    return 0


if __name__ == "__main__":
    sys.exit(main())