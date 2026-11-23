# Corpus Plan

## Purpose

This plan identifies the legal texts Jurideazor needs, explains how they relate to Law 90-11 or the Ahmed case, and records their verification status.

The full text metadata and links are recorded in `data/corpus_index.csv`.

## Metadata field definitions

- `rank` records the text's level in the legal hierarchy: 1 = Constitution; 2 = law, ordinance, or legislative decree; 3 = decree; 4 = order; 5 = circular. Law 90-11 and Legislative Decree 94-03 are both assigned rank 2 because a legislative decree has the force of law.
- `status` records whether the text's identity and source have been checked. Use `verified` only after opening the link and checking the text's number, title, and date. Checking whether the provisions relevant to the Ahmed case have been read is a separate task and should be recorded separately.
- `relation` describes how a text relates to another legal text. Use `standalone` for supporting texts that do not amend Law 90-11, including L-88-07, L-90-03, and L-90-04. Leave `target_articles` empty for these texts.

## 1. Base law and related texts

| Text ID | Text | Date | Official Gazette | Relationship and target articles | Status |
|---|---|---|---|---|---|
| L-90-11 | Law 90-11 on Labour Relations | 1990-04-21 | No. 17, 1990 | Base law for the project | verified |
| L-91-29 | Law 91-29 | 1991-12-21 | No. 68, 1991 | Modifies Article 73 and adds Articles 73-1 through 73-6 | verified |
| D-94-03 | Legislative Decree 94-03 | 1994-04-11 | No. 20, 1994 | Completes Law 90-11 by adding Article 87 bis | verified |
| O-96-21 | Ordinance 96-21 | 1996-07-09 | No. 43, 1996 | Modifies and completes multiple articles; see `corpus_index.csv` for the full target list | verified |
| O-97-02 | Ordinance 97-02 | 1997-01-11 | No. 3, 1997 | Completes Law 90-11 by adding Articles 52 bis, 52 ter and 52 quater | verified |
| O-97-03 | Ordinance 97-03 | 1997-01-11 | No. 3, 1997 | Sets the statutory working time and repeals Articles 22-26 of Law 90-11 | verified |
| O-15-01 | Ordinance 15-01, Supplementary Finance Law for 2015 | 2015-07-23 | No. 40, 2015 | Article 54 modifies and completes Articles 140 and 149 of Law 90-11 | verified |
| L-22-16 | Law 22-16 | 2022-07-20 | No. 49, 2022 | Completes Law 90-11 by adding Articles 56 bis through 56 bis 6 | verified |

## 2. Additional texts required for the Ahmed case

The following four texts must be collected into `data/raw` so the system can retrieve and cite them. The French and Arabic official Gazette links are listed here and must also be recorded in `data/corpus_index.csv`.

| Text | Type | Date | Gazette issue | French official text | Arabic official text | Relationship and target articles | Status |
|---|---|---|---|---|---|---|---|
| 88-07, hygiene, safety and occupational medicine | Law | 1988-01-26 | No. 4, 1988 | https://www.joradp.dz/FTP/Jo-Francais/1988/F1988004.pdf | https://www.joradp.dz/FTP/Jo-Arabe/1988/A1988004.pdf | Standalone supporting law; no amendment relationship to Law 90-11. Relevant provisions for Ahmed still need to be checked in the official text. | verified |
| 90-03, Labour Inspection | Law | 1990-02-06 | No. 6, 1990 | https://www.joradp.dz/FTP/Jo-Francais/1990/F1990006.pdf | https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990006.pdf | Standalone supporting law; no amendment relationship to Law 90-11. Relevant provisions for Ahmed still need to be checked in the official text. | verified |
| 90-04, settlement of individual labour disputes | Law | 1990-02-06 | No. 6, 1990 | https://www.joradp.dz/FTP/Jo-Francais/1990/F1990006.pdf | https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990006.pdf | Standalone supporting law; no amendment relationship to Law 90-11. Relevant provisions for Ahmed still need to be checked in the official text. | verified |
| 17-11, Finance Law for 2018 | Law | 2017-12-27 | No. 76, 2017 | https://www.joradp.dz/FTP/jo-francais/2017/F2017076.pdf | https://www.joradp.dz/FTP/jo-arabe/2017/A2017076.pdf | Article 98 modifies Articles 37-39 of Law 88-07. Article 99 modifies and completes several penalty articles in Law 90-11, including Articles 143 and 143 bis. | verified |

### Corpus perimeter

The `within_scope` field indicates whether a text belongs to the project's legal corpus on Law 90-11. Use `yes` for Law 90-11 itself and for texts that amend, supplement, repeal, or implement it. Use `no` for supporting labor-law texts that are relevant to the case but do not directly modify or implement Law 90-11.



