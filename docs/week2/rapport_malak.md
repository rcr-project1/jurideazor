# Rapport de contribution – Malak Aliouat
## Projet Jurideazor – Structuration des données juridiques

### 1. Introduction

Dans le cadre du projet Jurideazor, ma contribution concerne principalement la structuration des textes juridiques et leur préparation pour le moteur de recherche.

L'objectif de ce travail est de transformer les textes juridiques bruts en unités organisées et exploitables par les différentes composantes du système RAG (Retrieval-Augmented Generation).

Ma contribution porte essentiellement sur deux étapes :
- Le découpage des textes juridiques en articles (*Splitting*).
- La transformation des articles et des textes en passages exploitables (*Chunking*).

### 2. Généralisation du découpage des textes (Splitting)

#### 2.1. Problématique

Au départ, le script `split_loi_90_11.py` était conçu spécifiquement pour la loi 90-11. Il ne permettait donc pas de traiter automatiquement l'ensemble des textes juridiques disponibles dans le projet.

Pour résoudre cette limitation, un nouveau script général a été développé : 

`src/structure/split_articles.py`

#### 2.2. Travail réalisé

Le nouveau mécanisme permet de traiter automatiquement les fichiers textuels en français et en arabe présents dans les répertoires :

- `data/processed/texts/`
- `data/processed/texts_ar/`

Le traitement comprend :
- La détection des références aux articles en français et en arabe.
- La reconnaissance de plusieurs formes de numérotation.
- La prise en charge des articles commençant par « 1er ».
- La gestion des suffixes français tels que « bis », « ter » et « quater ».
- La prise en charge de certaines variantes de numérotation des sous-articles arabes.
- La conservation des textes ne contenant pas d'articles numérotés sous forme d'un seul enregistrement.
- La conservation du préambule lorsqu'il est présent et suffisamment long.

Le script extrait également les métadonnées nécessaires à l'identification de chaque unité juridique, notamment la langue, l'année, le type du texte et le fichier source.

#### 2.3. Résultats produits

Le processus de découpage génère les fichiers suivants :

| Fichier | Description |
|---|---|
| `data/processed/articles_all.json` | Ensemble des articles extraits des textes français et arabes |
| `data/processed/split_report.csv` | Rapport récapitulatif du découpage par fichier |

Ces résultats permettent de disposer d'une structure commune pour les différents textes juridiques du corpus.

### 3. Génération des passages (Chunking)

#### 3.1. Objectif

Après le découpage des textes en articles, une deuxième étape consiste à préparer des passages adaptés à la recherche documentaire et au calcul des embeddings.

Cette étape est importante, car les textes juridiques peuvent être longs et ne doivent pas nécessairement être traités en un seul bloc.

#### 3.2. Travail réalisé

Un script dédié a été développé :

`src/structure/chunk_texts.py`

Le traitement distingue deux situations :

**Cas 1 : Textes contenant des articles**

Chaque article est conservé comme une unité indépendante. Un article constitue donc un chunk, sans découpage supplémentaire de son contenu à cette étape.

**Cas 2 : Textes sans articles numérotés**

- Les textes courts sont conservés dans un seul chunk.
- Les textes longs sont divisés en passages en utilisant les paragraphes comme limites de séparation.
- Une limite d'environ 500 mots est utilisée comme référence pour la taille des passages.

L'objectif est de conserver le contenu juridique tout en produisant des unités plus faciles à exploiter par le moteur de recherche.

#### 3.3. Métadonnées et identifiants

Chaque chunk contient des informations permettant de retrouver son origine :

- `chunk_id` : identifiant unique du passage.
- `source_file` : fichier juridique d'origine.
- `lang` : langue du texte.
- `year` : année associée au document.
- `text_type` : type du document juridique.
- `article` : numéro de l'article, lorsqu'il existe.
- `content` : contenu textuel du passage.
- `char_count` : nombre de caractères.

Une amélioration a également été apportée à la génération des identifiants :
- Ajout d'un préfixe correspondant à la langue (`fr` ou `ar`).
- Gestion des doublons pour éviter les collisions entre les identifiants.
- Garantie de l'unicité des identifiants générés.

#### 3.4. Fichiers générés

| Fichier | Description |
|---|---|
| `data/processed/chunks.json` | Ensemble des passages préparés pour la recherche |
| `data/processed/chunk_report.csv` | Rapport statistique sur les chunks générés |

### 4. Vérifications et améliorations techniques

Des vérifications ciblées ont été réalisées afin de contrôler le comportement des scripts.

Les cas vérifiés comprennent notamment :

- La reconnaissance de `Art. 73`.
- La reconnaissance de `Art. 73 bis`.
- La prise en charge d'une numérotation arabe telle que `73 - 4`.
- La distinction des identifiants français et arabes.
- La gestion des identifiants dupliqués.

Ces améliorations visent à réduire les erreurs de détection des articles et à garantir une meilleure organisation des données produites.

### 5. Intégration dans le projet

Les scripts de découpage et de génération des chunks sont intégrés dans la branche :

`feat/semantic-search`

Les modifications ont été enregistrées à travers plusieurs commits Git et intégrées avec les changements de l'équipe.

Les fichiers générés automatiquement et les rapports de traitement sont gérés séparément du code source afin d'éviter d'ajouter inutilement des données volumineuses ou reproductibles au dépôt.

### 6. Relation avec le moteur de recherche

Le travail de Splitting et de Chunking constitue une étape préparatoire essentielle pour le moteur de recherche juridique.

Les passages produits peuvent ensuite être utilisés pour construire les index nécessaires à la recherche par mots-clés et à la recherche sémantique.

La comparaison entre BM25 et E5, ainsi que l'évaluation de leurs performances, relève de la contribution de Nouha et n'est donc pas présentée ici comme un travail personnel.

### 7. Conclusion

Ma contribution au projet Jurideazor a principalement porté sur la généralisation du découpage des textes juridiques et la préparation des passages destinés à la recherche documentaire.

Le développement de `split_articles.py` permet de dépasser la limitation d'un traitement spécifique à la loi 90-11 et de prendre en charge les textes français et arabes du corpus.

Le développement de `chunk_texts.py` permet ensuite de produire des unités structurées, accompagnées de leurs métadonnées et d'identifiants uniques.

Ces deux étapes contribuent à améliorer l'organisation, la traçabilité et l'exploitabilité des données juridiques dans le système Jurideazor.