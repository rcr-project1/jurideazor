# Knowledge Graph Ontology — Jurideazor

## 1. Entity Types

### Law

| Property | Type | Required | Description |
|---|---|---|---|
| `law_id` | string | yes | Unique node key; `text_id` from `corpus_index.csv` (e.g. `L-90-11`). |
| `number` | string | yes | Official law number (e.g. `90-11`); used to map raw identifiers to the canonical `law_id`. |
| `type` | string (enum) | yes | `law`, `ordinance`, or `legislative_decree` from `type`. |
| `date` | date | yes | Promulgation/publication date (`YYYY-MM-DD`). |
| `jo_year` | integer | yes | Official Gazette year. |
| `jo_issue` | integer | yes | Official Gazette issue number. |
| `url_fr` | string | yes | French JORADP source URL. |
| `url_ar` | string | yes | Arabic JORADP source URL. |
| `languages` | list[string] | yes | Parsed from `language` (`fr;ar` → `["fr","ar"]`). |
| `rank` | integer | yes | Legal hierarchy rank (1–5; all 12 corpus texts are rank 2). |
| `status` | string | yes | Verification status (`verified` in all rows). |
| `within_scope` | boolean | yes | `yes`/`no`; whether the text belongs to the Law 90-11 corpus. |
| `source` | string | yes | Provenance (`JORADP`). |
| `checked_on` | date | yes | Date the source was verified. |
| `notes` | string | no | Free-text note from `notes`. |
| `relation` | string | no | Raw CSV relation tag (e.g. `modifies;completes`), kept for provenance; edges are authoritative. |

### Article

| Property | Type | Required | Description |
|---|---|---|---|
| `article_id` | string | yes | Unique node key `{law_id}:{article_number}` (e.g. `L-90-11:73`). |
| `law_id` | string | yes | Foreign key to `Law.law_id`; exactly one owning Law. |
| `article_number` | string | yes | Article label from `article` (e.g. `73`, `73-1`, `56 bis`, `preambule`). |
| `content_fr` | string | no | French text; null when no French extraction exists. |
| `content_ar` | string | no | Arabic text; null when no Arabic extraction exists. |
| `char_count_fr` | integer | no | `char_count` of the French record. |
| `char_count_ar` | integer | no | `char_count` of the Arabic record. |
| `source_file_fr` | string | no | `source_file` of the French record. |
| `source_file_ar` | string | no | `source_file` of the Arabic record. |
| `year` | integer | no | Year from the record; for referenced-only nodes, derived from `Law.date`. |
| `text_type` | string | no | `text_type` from the record (e.g. `loi`, `ordonnance`, `decret`). |
| `current_status` | string (enum) | no | `in_force`, `modified`, `completed`, `repealed`; from `article_versions.json` for the 72 tracked articles. |
| `replaced_by` | string | no | Replacement reference when present (e.g. `ordonnance-97-03, article 2` for Art. 22; the repeal itself is by Art. 8 of the same ordinance). |

French and Arabic records are merged into one Article node by matching on the law ID and article number. The key is (source_file law identifier, article number). When one language is missing, the Article node is created with the available language only and the other content field is null. If duplicate records exist for the same law + article + language, the first record is kept and a validation warning is logged.

### Version

| Property | Type | Required | Description |
|---|---|---|---|
| `version_id` | string | yes | Unique node key `{article_id}:v{version_number}` (e.g. `L-90-11:73:v2`). |
| `article_id` | string | yes | Foreign key to `Article.article_id`; exactly one owning Article. |
| `law_id` | string | yes | `law` from `article_versions.json` mapped to the canonical Law ID (e.g. `L-90-11`). |
| `version_number` | integer | yes | `version` (1-based, contiguous). |
| `date` | date | yes | Date of the version. |
| `source` | string | yes | Amending instrument ID (`source`, e.g. `loi-91-29`); free string, may reference a law outside the 12 Law nodes. |
| `source_article` | string | no | Article number in the source instrument (`source_article`). |
| `action` | string (enum) | yes | `original`, `modified`, `added`, `completed`, `repealed`. |
| `summary_fr` | string | no | French summary. |
| `summary_ar` | string | no | Arabic summary. |
| `is_current` | boolean | yes | True iff `version_number` is the maximum for its Article. |

### Identifier Mapping

| Source file | Raw format | Example | Canonical node ID |
|---|---|---|---|
| `corpus_index.csv` | `text_id` column | `L-90-11` | `L-90-11` (use as-is) |
| `articles_all.json` | `source_file` path | `texts/1990/loi-90-11.txt` | Extract `loi-90-11`, map to `L-90-11` using `corpus_index.csv` |
| `article_versions.json` | `law` field | `90-11` | Prefix with type from `corpus_index.csv` → `L-90-11` |
| `article_versions.json` | `source` field | `loi-91-29` | Map to `L-91-29` using `corpus_index.csv` |
| `corpus_index.csv` | `target_articles` | `90-11:73` | Law part `90-11` → `L-90-11`, article part `73` → Article node `L-90-11:73` |

The canonical Law ID is the `text_id` from `corpus_index.csv` (e.g. `L-90-11`, `O-96-21`, `D-94-03`). The canonical Article ID is `{law_id}:{article_number}` (e.g. `L-90-11:73`, `L-90-11:56 bis`). The canonical Version ID is `{article_id}:v{version_number}` (e.g. `L-90-11:73:v1`).

## 2. Relation Types

### CONTAINS (Law → Article)

Ownership: the Law contains the Article.

| Property | Type | Required | Description |
|---|---|---|---|
| `ordinal` | integer | no | Zero-based position of the Article in the Law's source order; null for referenced-only Articles. |

### MODIFIES (Article → Article)

The source Article amends the text of the target Article.

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | date | yes | Date of the amendment. |
| `source_law` | string | yes | Number of the amending law (e.g. `91-29`). |
| `source_article` | string | yes | Article number in the amending law that carries the operation (e.g. `2`). |
| `action` | string (enum) | yes | Always `modified`. |

### COMPLETES (Article → Article)

The source Article adds or supplements the target Article.

In Algerian legal terminology, 'complète' covers both supplementing an existing article and introducing an entirely new article (e.g., Art. 56 bis added by loi 22-16). The Version action distinguishes these: 'completed' for supplements, 'added' for new articles.

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | date | yes | Date of the addition/completion. |
| `source_law` | string | yes | Number of the amending law (e.g. `22-16`). |
| `source_article` | string | yes | Article number in the amending law that carries the operation (e.g. `2`). |
| `action` | string (enum) | yes | `added` for a new article, `completed` for a supplement to an existing article. |

### REPEALS (Article → Article)

The source Article repeals the target Article.

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | date | yes | Date of the repeal. |
| `source_law` | string | yes | Number of the repealing law (e.g. `97-03`). |
| `source_article` | string | yes | Article number in the repealing law that carries the repeal (e.g. `8`). |
| `action` | string (enum) | yes | Always `repealed`. |

### HAS_VERSION (Article → Version)

The Article has the Version in its history.

| Property | Type | Required | Description |
|---|---|---|---|
| `version_number` | integer | yes | Version ordinal, equal to `Version.version_number`. |
| `is_current` | boolean | yes | True iff this is the Article's latest version. |

### SUPERSEDES (Version → Version)

The source Version replaces the target Version (newer → older).

| Property | Type | Required | Description |
|---|---|---|---|
| `date` | date | yes | Date of the superseding (source) Version. |
| `action` | string (enum) | yes | Action of the superseding (source) Version (`modified`, `added`, `completed`, `repealed`). |
| `source_law` | string | yes | Source law of the superseding (source) Version. |

## 3. Constraints

1. **Single ownership.** Every Article has exactly one incoming `CONTAINS` edge from exactly one Law, and `Article.law_id` equals that Law's `law_id`. An Article is never shared between laws.
2. **Cross-law amendment.** `MODIFIES`, `COMPLETES`, and `REPEALS` only connect Articles whose `law_id` values differ. No Article amends, completes, or repeals an Article of its own law.
3. **Version sequence.** For each Article, `version_number` values are unique and contiguous from `1` to `n` (no gaps, no duplicates). An Article may have zero Versions when no history is tracked; if `n > 0`, version `1` exists.
4. **Linear supersession.** `SUPERSEDES` only connects two Versions of the same Article and only `v+1 → v` (newer replaces older). Each Version has at most one outgoing and at most one incoming `SUPERSEDES` edge, forming one acyclic chain per Article. Version dates are non-increasing along the arrow direction (newer → older).
5. **Status consistency.** A `REPEALS` edge into Article `A` requires `A.current_status = "repealed"` and `A`'s latest Version `action = "repealed"`. Conversely, if `A.current_status = "repealed"`, its latest Version must have `action = "repealed"`. The repeal may come from a law outside the 12 Law nodes (e.g. Art. 87 bis repealed by `loi-14-10`); in that case no `REPEALS` edge is required.
6. **Endpoint and provenance integrity.** Every edge endpoint is an existing node. Every Version has exactly one incoming `HAS_VERSION` edge. Every `MODIFIES`/`COMPLETES`/`REPEALS` edge carries the same `date`, `source_law`, and `source_article` as the Version entry that justifies it. `Version.source` is a free law identifier and need not resolve to a Law node.

## 4. Example Subgraphs

### Art. 73 of Law 90-11 — modified by Law 91-29, Art. 2

```
(L-90-11:Law {number:"90-11", date:"1990-04-21"})
  +--CONTAINS--> (L-90-11:73:Article {article_number:"73", current_status:"modified"})
                   +--HAS_VERSION--> (L-90-11:73:v1:Version {version:1, date:"1990-04-21",
                   |                  source:"loi-90-11", action:"original"})
                   +--HAS_VERSION--> (L-90-11:73:v2:Version {version:2, date:"1991-12-21",
                                      source:"loi-91-29", source_article:"2", action:"modified"})
                   (L-90-11:73:v2) --SUPERSEDES--> (L-90-11:73:v1)

(L-91-29:Law {number:"91-29", date:"1991-12-21"})
  +--CONTAINS--> (L-91-29:2:Article {article_number:"2"})
                   +--MODIFIES {date:"1991-12-21", source_law:"91-29",
                                source_article:"2"}--> (L-90-11:73)
```

### Art. 22 of Law 90-11 — repealed by Ordinance 97-03, Art. 8

```
(L-90-11:Law {number:"90-11"})
  +--CONTAINS--> (L-90-11:22:Article {article_number:"22", current_status:"repealed"})
                   +--HAS_VERSION--> (L-90-11:22:v1:Version {version:1, date:"1990-04-21",
                   |                  source:"loi-90-11", action:"original"})
                   +--HAS_VERSION--> (L-90-11:22:v2:Version {version:2, date:"1997-01-11",
                                      source:"ordonnance-97-03", source_article:"8",
                                      action:"repealed"})
                   (L-90-11:22:v2) --SUPERSEDES--> (L-90-11:22:v1)

(O-97-03:Law {number:"97-03", date:"1997-01-11"})
  +--CONTAINS--> (O-97-03:8:Article {article_number:"8"})
                   +--REPEALS {date:"1997-01-11", source_law:"97-03",
                               source_article:"8"}--> (L-90-11:22)
```

### Art. 56 bis of Law 90-11 — added by Law 22-16, Art. 2

```
(L-90-11:Law {number:"90-11"})
  +--CONTAINS--> (L-90-11:56 bis:Article {article_number:"56 bis", current_status:"in_force"})
                   +--HAS_VERSION--> (L-90-11:56 bis:v1:Version {version:1, date:"2022-07-20",
                                      source:"loi-22-16", source_article:"2", action:"added"})

(L-22-16:Law {number:"22-16", date:"2022-07-20"})
  +--CONTAINS--> (L-22-16:2:Article {article_number:"2"})
                   +--COMPLETES {date:"2022-07-20", source_law:"22-16",
                                 source_article:"2"}--> (L-90-11:56 bis)
```

Art. 56 bis has a single Version, so no `SUPERSEDES` edge exists. The same operation creates `L-90-11:56 bis 1` through `L-90-11:56 bis 6`; each has one `COMPLETES` edge from `L-22-16:2` and one `v1` Version with `action:"added"`.

## 5. Design Decisions

- **No LegalConcept type.** `articles_all.json` and `article_versions.json` carry no concept or topic annotations. A concept layer would require labels not grounded in the source files; legal reasoning is handled at retrieval and answer time, while the graph stays a provenance and version graph.
- **One Article node with merged FR/AR content.** The article number is the stable join key across languages. One node keeps a single `HAS_VERSION` chain and a single set of amendment edges per article. `content_fr` and `content_ar` are optional, so a missing translation does not create a phantom second article.
- **Version is a node, not an edge property.** Each Version carries its own `date`, `action`, `source`, `source_article`, `summary_fr`, and `summary_ar`. Keeping it as a node avoids duplicating that metadata on every edge and makes the `SUPERSEDES` chain and status queries explicit.
- **NetworkX.** The graph is small (12 laws, 527 articles, 127 versions) and fits in memory. NetworkX provides directed multigraphs for the six relation types without a server, and installs as a normal Python dependency. Neo4j would add operational overhead without a query need.

## 6. Graph Statistics (measured)

| Item | Count | Derivation |
|---|---:|---|
| Law nodes | 12 | 12 rows in `data/corpus_index.csv`. |
| Article nodes with content | 518 | Unique `(law_id, article_number)` pairs from `data/processed/articles_all.json`, French and Arabic records merged, restricted to the 12 corpus texts; `law_id` derived from `source_file`. |
| Article nodes referenced only | 9 | `L-90-11:56 bis` … `L-90-11:56 bis 6` (from versions), `O-15-01:54`, `O-96-21:4` (edge endpoints absent from `articles_all.json`). |
| Article nodes (total) | 527 | 518 + 9. |
| Version nodes | 127 | Sum of all `versions` arrays in `article_versions.json` (72 articles). |
| `CONTAINS` edges | 527 | One per Article node. |
| `MODIFIES` edges | 31 | See the per-source table below. |
| `COMPLETES` edges | 42 | See the per-source table below. |
| `REPEALS` edges | 5 | See the per-source table below. |
| `HAS_VERSION` edges | 127 | One per Version node. |
| `SUPERSEDES` edges | 55 | `Σ(len(versions) − 1)` over the 72 articles: 127 − 72. |

`articles_all.json` contains 3,398 records across 441 source files; the 518 figure is the scope of the 12 texts in `corpus_index.csv`. The 518 include 11 `preambule` records; excluding them leaves 507 article-number nodes. `O-15-01` has 0 records in `articles_all.json`, so `O-15-01:54` is a referenced-only node.

Per-source split of `MODIFIES`, `COMPLETES`, and `REPEALS` from `corpus_index.csv` `target_articles`, disambiguated with the `notes` column and cross-checked against the `action` values in `article_versions.json`. The CSV alone gives 78 target pairs; the 31/42/5 split is not encoded in the `relation` column alone, so the split is derived from the `notes` column plus the Version `action` values.

| Source text | Target articles | `MODIFIES` | `COMPLETES` | `REPEALS` |
|---|---:|---:|---:|---:|
| L-91-29 | 7 | 1 | 6 | 0 |
| D-94-03 | 1 | 0 | 1 | 0 |
| O-96-21 | 36 | 11 | 25 | 0 |
| O-97-02 | 3 | 0 | 3 | 0 |
| O-97-03 | 5 | 0 | 0 | 5 |
| O-15-01 | 2 | 2 | 0 | 0 |
| L-22-16 | 7 | 0 | 7 | 0 |
| L-17-11 | 17 | 17 | 0 | 0 |
| **Total** | **78** | **31** | **42** | **5** |

Derivation script:

```bash
git show origin/add-article-versions:article_versions.json > /tmp/article_versions.json
python3 - <<'PY'
import csv, json, os, collections

rows = list(csv.DictReader(open("data/corpus_index.csv")))
articles = json.load(open("data/processed/articles_all.json"))
versions = json.load(open("/tmp/article_versions.json"))

num_to_id = {r["number"]: r["text_id"] for r in rows}
file_to_id, source_to_id = {}, {}
for r in rows:
    n, t = r["number"], r["type"]
    if t == "law":
        file_to_id[f"loi-{n}"] = source_to_id[f"loi-{n}"] = r["text_id"]
    elif t == "ordinance":
        file_to_id[f"ordonnance-{n}"] = source_to_id[f"ordonnance-{n}"] = r["text_id"]
    elif t == "legislative_decree":
        file_to_id[f"decret-{n}"] = source_to_id[f"decret-legislatif-{n}"] = r["text_id"]

def law_of(sf):
    return file_to_id.get(os.path.basename(sf).removesuffix(".txt"))

content = {(law_of(a["source_file"]), a["article"]) for a in articles if law_of(a["source_file"])}
refs = set()
for r in rows:
    for t in filter(None, r["target_articles"].split(";")):
        law, art = t.split(":", 1)
        refs.add((num_to_id[law], art))
for a in versions:
    refs.add((num_to_id[a["law"]], a["article"]))
    for v in a["versions"]:
        if "source_article" in v and v["source"] in source_to_id:
            refs.add((source_to_id[v["source"]], v["source_article"]))

print("Law nodes", len(rows))
print("Article nodes with content", len(content))
print("Referenced-only Article nodes", len(refs - content))
print("Article nodes total", len(content | refs))
print("Version nodes", sum(len(a["versions"]) for a in versions))
print("CONTAINS", len(content | refs))
print("HAS_VERSION", sum(len(a["versions"]) for a in versions))
print("SUPERSEDES", sum(len(a["versions"]) - 1 for a in versions))

counts = collections.Counter()
for a in versions:
    for v in a["versions"]:
        if v["action"] == "modified":
            counts["MODIFIES"] += 1
        elif v["action"] in ("added", "completed"):
            counts["COMPLETES"] += 1
        elif v["action"] == "repealed" and v["source"] in source_to_id:
            counts["REPEALS"] += 1
for r in rows:
    if r["text_id"] == "L-17-11":
        for t in filter(None, r["target_articles"].split(";")):
            if t.startswith("88-07:"):
                counts["MODIFIES"] += 1
print("MODIFIES", counts["MODIFIES"])
print("COMPLETES", counts["COMPLETES"])
print("REPEALS", counts["REPEALS"])
PY
```
