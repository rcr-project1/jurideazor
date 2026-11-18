# Sources and terms of use

> Week 2 — automated collection. Verification performed on **2026-11-16**.

## 1. Checks performed

| Check | Command / URL | Result |
|---|---|---|
| `robots.txt` (root) | `https://joradp.dz/robots.txt` | **HTTP 404 — File or directory not found** |
| `robots.txt` (`www` host) | `https://www.joradp.dz/robots.txt` | 404 |
| `robots.txt` (http) | `http://www.joradp.dz/robots.txt` | 404 |
| Legal notice | `joradp.dz` home page | *(to be completed)* |
| Ministry of Commerce `robots.txt` | *(site concerned)* | **disallows automated access → not crawled** |
| UpGrowth dataset page | `https://www.upgrowth.dz/datasets/journal-officiel-1962-2026` | reachable, files free under CC BY 4.0 |

**Evidence:** screenshot of the 404 response (`docs/week2/`), dated 2026-11-16.

## 2. Sources table

| Source | URL | `robots.txt` / licence | Result / date | Decision |
|---|---|---|---|---|
| JORADP (official) | `https://www.joradp.dz/` | `/robots.txt` | **404 — no file** (2026-11-16) | Collection allowed, with politeness |
| JORADP (`www`, http) | `http://www.joradp.dz/robots.txt` | — | 404 | Same decision |
| Ministry of Commerce | — | **crawling disallowed** | — | **Not crawled** |
| UpGrowth — JORADP index | `https://www.upgrowth.dz/datasets/journal-officiel-1962-2026` | **CC BY 4.0** (index only) | 5,288 issues, 10,413 links (updated 2026-09-09) | Used **only** to get the issue list and PDF URLs |
| WIPO Lex | `https://www.wipo.int/wipolex/fr/legislation/details/14834` | public page, unofficial mirror | — | **Temporary fallback** for Law 90-11 (1997 consolidated version); final source remains JORADP (see §5.2) |

## 3. Interpretation of the JORADP `robots.txt` (RFC 9309)

- A **4xx** response ("unavailable") means no restriction is declared: access is **allowed**.
- A **5xx** response would have been interpreted as a **complete disallow**.
- The absence of `robots.txt` removes neither the site's terms of use nor the requirement of polite collection.

## 4. Secondary source: the UpGrowth index (CC BY 4.0)

**What it is.** A third-party open index of the Official Journal, published by UpGrowth (a private Algerian business-services platform). It is **not** an official State source, and it is **not** a text corpus.

| Item | Value |
|---|---|
| Issues indexed | 5,288 (1962 → 2026) |
| PDF links | 10,413 (5,287 FR + 5,126 AR), each verified against `joradp.dz` |
| Second file | `jo-ref-index.json` — 12,870 text references, 2002 → 2026 (2,017 issues) |
| Columns (CSV) | `year`, `issue`, `edition_fr`, `edition_ar`, `url_fr`, `url_ar`, `year_fully_probed`, `ug_ref` (8 columns) |
| Files used | `journal-officiel-archive.csv` (752,103 B), `jo-ref-index.json` (860,626 B) |
| Licence | **CC BY 4.0** — applies to the index, **never** to the State PDFs |
| Hosting | UpGrowth hosts **no PDF**; links point to `joradp.dz` |

### 4.1 Downloaded files and integrity record

Downloaded on **2026-11-16** with `curl -sSL`, stored outside Git (`data/raw/joradp/index/`).

| File | Bytes | SHA-256 | Recorded |
|---|---|---|---|
| `journal-officiel-archive.csv` | 752,103 | `5732e90e4b4810724e094754472a0b05328303187664d8a68abd52135fc063ae` | 2026-11-16 |
| `jo-ref-index.json` | 860,626 | `f90b6d289a2ec6ac6f80769ab3966680c28a1e3f893fb6f5b504fed308c17f94` | 2026-11-16 |

Reproduce with:

```bash
cd data/raw/joradp/index
sha256sum journal-officiel-archive.csv jo-ref-index.json
```

Note: the dataset page announces 626 KB for the CSV; the downloaded file is 752,103 B. The content matches the announced structure (5,288 rows × 8 columns, last row `2026/57`), so the size difference is not an error — the file was updated after the page text. **The hash above is the reference**, not the announced size.

**Attribution used in the report (required by CC BY 4.0):**

> UpGrowth (2026), *Index du Journal officiel algérien : 5 288 numéros, 1962 à 2026*, upgrowth.dz/datasets/journal-officiel-1962-2026, CC BY 4.0.

**Limits acknowledged:**

- Index only: no publication date, no `SOMMAIRE`, no article titles, no subject classification — splitting, filtering and OCR remain **our** work.
- **All issues before 2002 are scanned images** (tested files 1965–2001 return zero characters) → OCR required. This includes the issues carrying the main amendments of Law 90-11 (68/1991, 20/1994, 3/1997).
- The **Arabic edition is a separate publication**, not a translation; it does not exist for 1962–1963 and 1964 stops at issue 64 (complete only from 1965).
- The CSV was probed on 2026-08-03 and stops at **issue 57/2026**; newer issues are not in the file.
- Links are not hosted by UpGrowth: if `joradp.dz` moves a file, the link breaks.
- The JSON goes further than the CSV (issue 62/2026): joining on `(year, issue)` leaves **5 issues unmatched**.
- The free **files** were used; the **paid API / data licence was not** (and must not be).

## 5. Collection policy and provenance

### 5.1 Polite collection measures applied

- Explicit `User-Agent` containing the university contact address.
- At least **3 seconds** between two requests.
- **No** parallel downloads.
- Volume limited to the issues actually needed (known issues + evaluation sample).
- No bypassing of any restriction; the Ministry of Commerce website is not crawled.
- Each text keeps its `source_url`, `jo_issue` and page; the original PDF is kept.
- `downloads.sqlite` registry (unique key `language-year-issue`, `sha256`, date) for duplicate-free re-runs.

### 5.2 Provenance of raw files (one register per question)

Two complementary registers, so the same information is never written twice:

| Question | Register | Content |
|---|---|---|
| *Where does this raw text file come from?* | `data/raw/PROVENANCE.md` | per file: title, source, version, articles covered, limitations |
| *Where does this PDF come from and is it intact?* | `data/processed/downloads_manifest.csv` (exported from `downloads.sqlite` by `src/collect/export_manifest.py`) | `k`, URL, SHA-256, size, fetch date, **relative** path |

The SQLite registry stays local (git-ignored, binary); the CSV export is the portable proof. This document answers *"may we collect this site, under which terms?"*; the two registers answer *"what exactly do we have, and where from?"*.

**Temporary fallback for Law 90-11.** The starting text of Law 90-11 is the **WIPO Lex** consolidated version (1997), an unofficial mirror. It is used **temporarily and explicitly**, for two reasons: the official JORADP issue of 21 April 1990 is a scanned image requiring OCR, and the consolidated 1997 text already integrates the amendments we study. Consequences, applied until replacement:

- every citation of Law 90-11 must be labelled **« version consolidée 1997 (WIPO) »** and its numbers/dates verified on the printed page (see the FR/AR evidence hierarchy in the week-2 report);
- the final source will be the **JORADP issue of 21 April 1990**, downloaded with the same script and OCR'd; the Arabic edition will then provide the Arabic version of the base law;
- article coverage in that file is **172 articles** (158 + `73-1` … `73-6`), not 158.

## 6. Text for the report

> **Sources and terms of use.**
> Before any automated collection, we checked the `robots.txt` file of the Official Journal website. The request `https://www.joradp.dz/robots.txt` returns **HTTP 404 (file not found)**: the site therefore publishes no exclusion file. Under RFC 9309, a 4xx response means that no restriction is declared and that access is allowed; a 5xx response would have been interpreted as a complete disallow. The absence of `robots.txt` does not exempt us from respecting the site's terms of use or from collecting politely: we clearly identify our client (`User-Agent` containing the university address), we enforce a delay of at least 3 seconds between requests, we perform no parallel downloads, and we limit the volume to the issues actually needed. The evidence of this verification (screenshot of the 404 response, dated 2026-11-16) is kept in `docs/week2/`. The **Ministry of Commerce** website, whose `robots.txt` disallows automated access, has not been crawled.
>
> **Issue list and URL discovery.** To avoid crawling the Official Journal index pages, we rely on the openly published index *"Index du Journal officiel algérien : 5 288 numéros, 1962 à 2026"* (UpGrowth, 2026, CC BY 4.0). It lists 5,288 issues and 10,413 PDF links (5,287 French, 5,126 Arabic), each verified one by one against `joradp.dz`, plus a second file of 12,870 text references for 2002–2026. This index is **not** an official source and **not** a text corpus: it contains no article title, no publication date and no subject classification. It is used only to obtain the list of issues and the official PDF URLs; splitting into articles, filtering labor-related texts, OCR and version tracking are our own work. We also note its documented limits: every issue before 2002 is a scanned image (hence OCR is mandatory, including for the 1991, 1994 and 1997 issues that carry the amendments of Law 90-11); the Arabic edition is a distinct publication, absent for 1962–1963 and incomplete in 1964; the CSV stops at issue 57 of 2026; and UpGrowth hosts none of the PDFs, so links may break if the Official Journal moves a file. The free files were used under CC BY 4.0; the paid API and data licence were not used.

## 7. To complete this week

- [x] 404 screenshot stored in `docs/week2/`.
- [ ] Legal notice / terms of use recorded, if any exist.
- [x] Index downloaded into `data/raw/joradp/index/` + hash recorded (2026-11-16, see §4.1).
- [x] List of selected issues (68/1991, 20/1994, 3/1997, 40/2015 + sample).
- [x] `downloads.sqlite` registry + proof of duplicate-free re-run: `0 fetched, 24 skipped, 0 failed` (2026-11-18), 19 registered PDFs, `issue`/`edition` columns.
- [x] OCR applied and measured on scanned issues (68/1991, 20/1994, 3/1997): OCR v2, 258 pages, CER 0.0250 on a 520-character Arabic sample, plus digit audit (`src/eval/`).
- [ ] Precision/Recall table of filtering on an annotated sample.
