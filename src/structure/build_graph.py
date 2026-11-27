import csv
import json
import os
import re
import sys
import warnings
from collections import defaultdict

import networkx as nx


# ============================================================
# 1. PATHS
# ============================================================

CORPUS_FILE = "data/corpus_index.csv"
ARTICLES_FILE = "data/processed/articles_all.json"
VERSIONS_FILE = "data/processed/article_versions.json"
RELATIONS_FILE = "data/processed/relations.json"

OUTPUT_FILE = "data/processed/knowledge_graph.graphml"


# ============================================================
# 2. LOAD DATA
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


with open(CORPUS_FILE, "r", encoding="utf-8-sig") as f:
    corpus = list(csv.DictReader(f))

articles_data = load_json(ARTICLES_FILE)
versions_data = load_json(VERSIONS_FILE)
relations_data = load_json(RELATIONS_FILE)


# ============================================================
# 3. IDENTIFIER MAPPING
# ============================================================

number_to_id = {}
file_to_id = {}
source_to_id = {}
law_info = {}

for law in corpus:
    number = law["number"].strip()
    text_id = law["text_id"].strip()
    law_type = law["type"].strip()

    number_to_id[number] = text_id
    law_info[text_id] = law

    if law_type == "law":
        prefix = "loi"
        source_prefix = "loi"

    elif law_type == "ordinance":
        prefix = "ordonnance"
        source_prefix = "ordonnance"

    elif law_type == "legislative_decree":
        prefix = "decret"
        source_prefix = "decret-legislatif"

    else:
        continue

    file_to_id[f"{prefix}-{number}"] = text_id
    source_to_id[f"{source_prefix}-{number}"] = text_id


def get_law_id(number):
    if number is None:
        return None
    return number_to_id.get(str(number).strip())


def get_source_law_id(source):
    if not source:
        return None

    source = str(source).strip()

    if source in source_to_id:
        return source_to_id[source]

    # Fallback for identifiers such as loi-90-11
    for prefix in ("loi-", "ordonnance-", "decret-legislatif-"):
        if source.startswith(prefix):
            number = source[len(prefix):]
            return get_law_id(number)

    return None


def get_file_law_id(source_file):
    basename = os.path.basename(source_file)
    basename = basename.removesuffix(".txt")
    return file_to_id.get(basename)


def article_id(law_id, number):
    return f"{law_id}:{str(number).strip()}"


# ---- Article references -------------------------------------------------
# A reference such as "140 et 149" or "22 à 26" designates SEVERAL articles.
# It must be expanded before creating nodes, otherwise the graph gets one
# fake "article" per reference string.

VALID_REF = re.compile(
    r"^\d+(?:-\d+)?(?: (?:bis|ter|quater)(?: \d+)?)?$"
)

# Known typos found in the source CSV / JSON (better to fix them at the source).
REF_ALIASES = {"1-73": "73-1"}

# An article number containing one of these is a grouped reference, not an id.
SUSPICIOUS_ID = re.compile(r",|;|\bet\b|\bà\b")

bad_refs = []


def expand_article_refs(raw):
    """Expand '140 et 149', '22 à 26', '73-1, 73-2' into a list of numbers."""
    if raw is None:
        return []

    text = re.sub(r"\s+", " ", str(raw)).strip()
    result = []

    for part in re.split(r"\s*[;,]\s*|\s+et\s+", text):
        part = REF_ALIASES.get(part.strip().lower(), part.strip().lower())

        if not part:
            continue

        range_match = re.fullmatch(r"(\d+) à (\d+)", part)

        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))

            if start <= end and end - start <= 50:
                result.extend(str(n) for n in range(start, end + 1))
                continue

        elif VALID_REF.match(part):
            result.append(part)
            continue

        bad_refs.append(f"{raw!r} -> {part!r}")

    return list(dict.fromkeys(result))


# ============================================================
# 4. CREATE DIRECTED MULTIGRAPH
# ============================================================

G = nx.MultiDiGraph()
G.graph["name"] = "Jurideazor Knowledge Graph"
G.graph["description"] = "Algerian labor law knowledge graph"


# Characters that are illegal in XML 1.0 (form feeds coming from PDF pages...).
XML_INVALID = re.compile(
    "[^\t\n\r\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]"
)


def clean_string(value):
    """Make a value safe for GraphML: illegal XML characters become a space."""
    return XML_INVALID.sub(" ", str(value))


def clean_attributes(attributes):
    """Convert attributes to GraphML-compatible values."""

    result = {}

    for key, value in attributes.items():
        if value is None:
            continue

        if isinstance(value, bool):
            result[key] = str(value).lower()

        elif isinstance(value, (list, tuple, set)):
            result[key] = clean_string(
                ";".join(str(x) for x in value)
            )

        elif isinstance(value, dict):
            result[key] = clean_string(
                json.dumps(value, ensure_ascii=False)
            )

        else:
            result[key] = clean_string(value)

    return result


def add_article(law_id, number, **attributes):
    """Create an Article node if it does not already exist."""
    if not law_id or number is None:
        return None

    number = str(number).strip()

    if not number:
        return None

    if SUSPICIOUS_ID.search(number):
        warnings.warn(f"Ignoring grouped article reference: {number!r}")
        bad_refs.append(f"{law_id}:{number!r} (grouped reference, no node created)")
        return None

    aid = article_id(law_id, number)

    if not G.has_node(aid):
        G.add_node(
            aid,
            **clean_attributes({
                "node_type": "Article",
                "article_id": aid,
                "law_id": law_id,
                "article_number": number,
                **attributes
            })
        )
    else:
        # Fill missing properties without replacing existing content.
        for key, value in clean_attributes(attributes).items():
            if key not in G.nodes[aid] or not G.nodes[aid][key]:
                G.nodes[aid][key] = value

    return aid


# ============================================================
# 5. CREATE LAW NODES
# ============================================================

for law in corpus:
    law_id = law["text_id"]

    languages = [
        x.strip()
        for x in law.get("language", "").split(";")
        if x.strip()
    ]

    G.add_node(
        law_id,
        **clean_attributes({
            "node_type": "Law",
            "law_id": law_id,
            "number": law.get("number"),
            "type": law.get("type"),
            "date": law.get("date"),
            "jo_year": law.get("jo_year"),
            "jo_issue": law.get("jo_issue"),
            "url_fr": law.get("url_fr"),
            "url_ar": law.get("url_ar"),
            "languages": languages,
            "rank": law.get("rank"),
            "status": law.get("status"),
            "within_scope": law.get("within_scope", "").lower() == "yes",
            "source": law.get("source"),
            "checked_on": law.get("checked_on"),
            "notes": law.get("notes"),
            "relation": law.get("relation")
        })
    )


# ============================================================
# 6. CREATE ARTICLE NODES AND MERGE FR / AR
# ============================================================

seen_languages = set()
article_ordinals = defaultdict(int)
duplicate_count = 0
unmatched_count = 0

for record in articles_data:

    law_id = get_file_law_id(record.get("source_file", ""))

    if law_id is None:
        unmatched_count += 1
        continue

    number = record.get("article")

    if number is None or str(number).strip() == "":
        continue

    number = str(number).strip()
    lang = str(record.get("lang", "")).lower().strip()

    aid = article_id(law_id, number)

    if not G.has_node(aid):
        article_ordinals[law_id] += 1

        add_article(
            law_id,
            number,
            year=record.get("year"),
            text_type=record.get("text_type"),
            ordinal=article_ordinals[law_id]
        )

    if not G.has_node(aid):
        continue

    language_key = (aid, lang)

    if language_key in seen_languages:
        duplicate_count += 1
        continue

    seen_languages.add(language_key)

    if lang == "fr":
        G.nodes[aid]["content_fr"] = clean_string(record.get("content", ""))
        G.nodes[aid]["char_count_fr"] = record.get("char_count", 0)
        G.nodes[aid]["source_file_fr"] = clean_string(record.get("source_file", ""))

    elif lang == "ar":
        G.nodes[aid]["content_ar"] = clean_string(record.get("content", ""))
        G.nodes[aid]["char_count_ar"] = record.get("char_count", 0)
        G.nodes[aid]["source_file_ar"] = clean_string(record.get("source_file", ""))


# ============================================================
# 7. ADD REFERENCED ARTICLES FROM CORPUS INDEX
# ============================================================

for law in corpus:
    targets = law.get("target_articles", "")

    for target in targets.split(";"):
        target = target.strip()

        if not target or ":" not in target:
            continue

        target_number, target_article = target.split(":", 1)
        target_law_id = get_law_id(target_number)

        if target_law_id:
            for number in expand_article_refs(target_article):
                add_article(target_law_id, number)


# ============================================================
# 8. CREATE VERSION NODES
# ============================================================

version_count = 0
version_groups = defaultdict(list)
versioned_ids = set()

for item in versions_data:

    target_law_id = get_law_id(item.get("law"))

    if target_law_id is None:
        warnings.warn(
            f"Unknown law in article_versions.json: {item.get('law')}"
        )
        continue

    target_number = str(item.get("article", "")).strip()

    if not target_number:
        continue

    aid = add_article(
        target_law_id,
        target_number,
        current_status=item.get("current_status")
    )

    if aid is None:
        continue

    versioned_ids.add(aid)

    versions = sorted(
        item.get("versions", []),
        key=lambda v: int(v.get("version", 0))
    )

    version_numbers = [
        int(v.get("version", 0))
        for v in versions
    ]

    if version_numbers:
        expected = list(range(1, len(version_numbers) + 1))

        if version_numbers != expected:
            warnings.warn(
                f"Non-contiguous versions for {aid}: {version_numbers}"
            )

    for index, version in enumerate(versions):

        v_number = int(version["version"])
        vid = f"{aid}:v{v_number}"

        is_current = index == len(versions) - 1

        G.add_node(
            vid,
            **clean_attributes({
                "node_type": "Version",
                "version_id": vid,
                "article_id": aid,
                "law_id": target_law_id,
                "version_number": v_number,
                "date": version.get("date"),
                "source": version.get("source"),
                "source_article": version.get("source_article"),
                "action": version.get("action"),
                "summary_fr": version.get("summary_fr"),
                "summary_ar": version.get("summary_ar"),
                "is_current": is_current
            })
        )

        G.add_edge(
            aid,
            vid,
            key=f"HAS_VERSION_{v_number}",
            relation="HAS_VERSION",
            version_number=v_number,
            is_current=str(is_current).lower()
        )

        version_groups[aid].append({
            "version_id": vid,
            "version_number": v_number,
            "date": version.get("date"),
            "source": version.get("source"),
            "source_article": version.get("source_article"),
            "action": version.get("action")
        })

        version_count += 1

        # Create the source Article node when the source is in the corpus.
        source_law_id = get_source_law_id(version.get("source"))
        source_article = version.get("source_article")

        if source_law_id and source_article:
            add_article(source_law_id, source_article)


# ============================================================
# 9. CREATE SUPERSEDES EDGES
# Newer version -> older version
# ============================================================

supersedes_count = 0

for aid, versions in version_groups.items():

    versions.sort(key=lambda v: v["version_number"])

    for older, newer in zip(versions, versions[1:]):

        G.add_edge(
            newer["version_id"],
            older["version_id"],
            key="SUPERSEDES",
            relation="SUPERSEDES",
            date=newer.get("date") or "",
            action=newer.get("action") or "",
            source_law=newer.get("source") or ""
        )

        supersedes_count += 1


# ============================================================
# 10. CREATE AMENDMENT RELATIONS FROM VERSION HISTORY
# ============================================================

action_to_relation = {
    "modified": "MODIFIES",
    "added": "COMPLETES",
    "completed": "COMPLETES",
    "repealed": "REPEALS"
}

amendment_count = defaultdict(int)
AMENDMENT_RELATIONS = ("MODIFIES", "COMPLETES", "REPEALS")
relation_conflicts = []


def add_amendment_edge(
    source_law_id,
    source_article,
    target_law_id,
    target_article,
    relation,
    date,
    source_law,
    action
):
    if not source_law_id or not target_law_id:
        return

    if not source_article or not target_article:
        return

    # Ontology requires cross-law amendment relations.
    if source_law_id == target_law_id:
        return

    source_id = add_article(source_law_id, source_article)
    target_id = add_article(target_law_id, target_article)

    if not source_id or not target_id:
        return

    # One amendment relation per (source article, target article) pair.
    # Version history runs first, so it wins over relations.json.
    existing = G.get_edge_data(source_id, target_id) or {}
    previous = [
        attrs.get("relation")
        for attrs in existing.values()
        if attrs.get("relation") in AMENDMENT_RELATIONS
    ]

    if previous:
        if relation not in previous:
            relation_conflicts.append(
                f"{source_id} -> {target_id}: kept {previous[0]}, skipped {relation}"
            )
        return

    edge_key = (
        f"{relation}_{source_id}_{target_id}_"
        f"{date}_{source_article}"
    )

    if G.has_edge(source_id, target_id, key=edge_key):
        return

    G.add_edge(
        source_id,
        target_id,
        key=edge_key,
        relation=relation,
        date=date or "",
        source_law=source_law or "",
        source_article=str(source_article),
        action=action or ""
    )

    amendment_count[relation] += 1


# Use version history as the primary source of amendment provenance.
for target_aid, versions in version_groups.items():

    target_law_id = G.nodes[target_aid]["law_id"]
    target_article = G.nodes[target_aid]["article_number"]

    for version in versions:

        action = str(version.get("action", "")).lower()
        relation = action_to_relation.get(action)

        if not relation:
            continue

        source_law_id = get_source_law_id(version.get("source"))
        source_article = version.get("source_article")

        add_amendment_edge(
            source_law_id=source_law_id,
            source_article=source_article,
            target_law_id=target_law_id,
            target_article=target_article,
            relation=relation,
            date=version.get("date"),
            source_law=version.get("source"),
            action=action
        )


# ============================================================
# 11. ADD RELATIONS FROM EXTRACTED RELATIONS.JSON
# Avoid duplicates already created from version history.
# ============================================================

for relation_record in relations_data:

    source_law_id = get_law_id(relation_record.get("source_law"))
    target_law_id = get_law_id(relation_record.get("target_law"))

    relation_name = str(
        relation_record.get("relation", "")
    ).lower().strip()

    relation_map = {
        "modifies": "MODIFIES",
        "completes": "COMPLETES",
        "repeals": "REPEALS"
    }

    relation = relation_map.get(relation_name)

    if not relation or not source_law_id or not target_law_id:
        continue

    source_article = relation_record.get("source_article")
    targets = relation_record.get("target_articles", "")

    if not source_article or not targets:
        continue

    if isinstance(targets, list):
        target_articles = [
            number
            for item in targets
            for number in expand_article_refs(item)
        ]
    else:
        target_articles = expand_article_refs(targets)

    source_date = law_info[source_law_id].get("date", "")
    source_number = law_info[source_law_id].get("number", "")

    for target_article in target_articles:

        target_article = str(target_article).strip()

        if not target_article:
            continue

        add_amendment_edge(
            source_law_id=source_law_id,
            source_article=source_article,
            target_law_id=target_law_id,
            target_article=target_article,
            relation=relation,
            date=source_date,
            source_law=source_number,
            action={
                "MODIFIES": "modified",
                "COMPLETES": "completed",
                "REPEALS": "repealed"
            }[relation]
        )


# ============================================================
# 12. ADD CONTAINS EDGES
# Every Article has exactly one owning Law.
# ============================================================

# Flag articles that exist in the graph but have no text in the corpus
# (referenced by an amendment, text not extracted). Search must skip them.
for node_id, attributes in G.nodes(data=True):
    if attributes.get("node_type") == "Article":
        has_text = bool(
            attributes.get("content_fr") or attributes.get("content_ar")
        )
        attributes["has_text"] = str(has_text).lower()

contains_count = 0

for node_id, attributes in list(G.nodes(data=True)):

    if attributes.get("node_type") != "Article":
        continue

    law_id = attributes.get("law_id")

    if law_id not in G:
        warnings.warn(f"Missing owning Law for Article {node_id}")
        continue

    G.add_edge(
        law_id,
        node_id,
        key="CONTAINS",
        relation="CONTAINS",
        ordinal=attributes.get("ordinal", "")
    )

    contains_count += 1


# ============================================================
# 13. VALIDATION
# ============================================================

errors = []

# Rule 1: Single ownership
for node_id, attrs in G.nodes(data=True):

    if attrs.get("node_type") != "Article":
        continue

    owners = [
        source
        for source, _, edge_attrs in G.in_edges(
            node_id, data=True
        )
        if edge_attrs.get("relation") == "CONTAINS"
    ]

    if len(owners) != 1:
        errors.append(
            f"Article {node_id} has {len(owners)} owners"
        )

    elif owners[0] != attrs.get("law_id"):
        errors.append(
            f"Ownership mismatch for {node_id}"
        )


# Rule 2: Cross-law amendment
for source, target, attrs in G.edges(data=True):

    if attrs.get("relation") not in (
        "MODIFIES", "COMPLETES", "REPEALS"
    ):
        continue

    source_law = G.nodes[source].get("law_id")
    target_law = G.nodes[target].get("law_id")

    if source_law == target_law:
        errors.append(
            f"Same-law amendment: {source} -> {target}"
        )


# Rule 3: Version sequence
for aid, versions in version_groups.items():

    numbers = sorted(v["version_number"] for v in versions)

    if numbers and numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"Invalid version sequence for {aid}")


# Rule 4: Linear supersession
for source, target, attrs in G.edges(data=True):

    if attrs.get("relation") != "SUPERSEDES":
        continue

    source_article = G.nodes[source].get("article_id")
    target_article = G.nodes[target].get("article_id")

    source_version = int(G.nodes[source].get("version_number", 0))
    target_version = int(G.nodes[target].get("version_number", 0))

    if source_article != target_article:
        errors.append(f"SUPERSEDES connects different articles: {source}, {target}")

    if source_version != target_version + 1:
        errors.append(f"Invalid SUPERSEDES sequence: {source}, {target}")


# Rule 5: Repeal status consistency
for aid, versions in version_groups.items():

    if not versions:
        continue

    latest = max(versions, key=lambda v: v["version_number"])
    status = G.nodes[aid].get("current_status", "")
    latest_action = latest.get("action", "")

    if status == "repealed" and latest_action != "repealed":
        errors.append(
            f"Repeal status mismatch for {aid}"
        )


# Rule 6: Endpoint and HAS_VERSION integrity
for node_id, attrs in G.nodes(data=True):

    if attrs.get("node_type") != "Version":
        continue

    incoming = [
        source
        for source, _, edge_attrs in G.in_edges(
            node_id, data=True
        )
        if edge_attrs.get("relation") == "HAS_VERSION"
    ]

    if len(incoming) != 1:
        errors.append(
            f"Version {node_id} has {len(incoming)} HAS_VERSION edges"
        )


# Rule 7: Versions are in chronological order (ISO dates compare as text)
for aid, versions in version_groups.items():
    dated = [v["date"] for v in versions if v.get("date")]

    if dated != sorted(dated):
        errors.append(f"Versions of {aid} are not in chronological order")


# Rule 8: No version after a repeal
for aid, versions in version_groups.items():
    ordered = sorted(versions, key=lambda v: v["version_number"])
    actions = [str(v.get("action", "")).lower() for v in ordered]

    if "repealed" in actions and actions.index("repealed") != len(actions) - 1:
        errors.append(f"Version found after repeal for {aid}")


# Rule 9: Every article listed in article_versions.json has >= 1 version
for aid in versioned_ids:
    if not version_groups.get(aid):
        errors.append(f"Article {aid} is in article_versions.json without versions")


# Rule 10: No fake article ids (grouped references such as "140 et 149")
for node_id, attrs in G.nodes(data=True):
    if (
        attrs.get("node_type") == "Article"
        and SUSPICIOUS_ID.search(attrs.get("article_number", ""))
    ):
        errors.append(f"Suspicious article id: {node_id}")


# ============================================================
# 14. SAVE GRAPH
# ============================================================

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

nx.write_graphml(G, OUTPUT_FILE)

# ============================================================
# 15. REPORT
# ============================================================

node_counts = defaultdict(int)
edge_counts = defaultdict(int)

for _, attrs in G.nodes(data=True):
    node_counts[attrs.get("node_type", "Unknown")] += 1

for _, _, attrs in G.edges(data=True):
    edge_counts[attrs.get("relation", "Unknown")] += 1

print("\n========== JURIDEAZOR KNOWLEDGE GRAPH ==========")

print("\nNODES:")
for name, count in sorted(node_counts.items()):
    print(f"{name}: {count}")

print("\nEDGES:")
for name, count in sorted(edge_counts.items()):
    print(f"{name}: {count}")

print("\nOTHER INFORMATION:")
print("Unmatched article records:", unmatched_count)
print("Duplicate language records:", duplicate_count)
print("Total nodes:", G.number_of_nodes())
print("Total edges:", G.number_of_edges())

no_text = sum(
    1 for _, a in G.nodes(data=True)
    if a.get("node_type") == "Article" and a.get("has_text") == "false"
)
print("Articles without text (has_text=false):", no_text)
print("Amendment conflicts skipped:", len(relation_conflicts))
print("Unparseable references:", len(bad_refs))

for line in bad_refs[:20]:
    print("  unparseable:", line)

for line in relation_conflicts[:20]:
    print("  conflict:", line)

print("\nVALIDATION:")
if errors:
    print(f"Found {len(errors)} validation issue(s):")
    for error in errors:
        print("-", error)
else:
    print("All implemented validation checks passed.")

print("\nGraph saved to:", OUTPUT_FILE)
print("================================================")

if errors:
    sys.exit(1)