# Week 2 Progress Report

**Project:** Jurideazor  
**Student:** Hadil  
**Reporting period:** Week 2

## 1. Work completed

### Corpus plan

I prepared a corpus plan describing the base law, Law 90-11 on Labour Relations, and the related texts identified for the project. The plan also lists four additional texts needed for the Ahmed case: Laws 88-07, 90-03, 90-04, and Finance Law 17-11 for 2018. These texts are intended to be collected in `data/raw` so that the system can retrieve and cite them.

### Corpus index

I started `data/corpus_index.csv` to record the legal texts and their metadata, including text type and number, date, Official Gazette issue, language links, relationship to the base law, and target articles. The base law is included as the reference text; related amendment or supplementary texts are recorded separately. The four Ahmed-case texts also need entries in the index, alongside copies of their source PDFs in `data/raw`.

### Relevance sample

I prepared `eval/relevance_sample.csv` with 20 Gazette documents from different issues: 10 marked as relevant to labour and 10 marked as not relevant. The file follows the guide's columns: `doc_id`, `source`, `title`, `is_labor`, `annotator`, and `note`.

In this sample, `annotator` means the person who made the relevance judgment. The current entries use `Hadil` for that person; it does not refer to an official who classified the Gazette document. `is_labor` records my judgment about whether the document concerns labour.

### Source register

I prepared `data/raw/sources.md` as a source register. It records WIPO Lex, JORADP, the UpGrowth index, NATLEX, and MTESS, along with what each source provides, its URL, the date checked, and its intended use. JORADP is identified as the primary place to check the official Gazette text; the other sources help locate texts or cross-check metadata.

## 2. Decisions made

- Law 90-11 is treated as the base law for the project's labour-law corpus.
- Texts that amend or supplement Law 90-11 are linked to it in the corpus metadata; separate laws needed for the Ahmed case are collected as supporting texts.
- The relevance sample is balanced: 10 labour-related documents and 10 documents outside the labour-law topic.


