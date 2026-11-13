# Jurideazor

Base de connaissances juridiques et assistant de raisonnement sur le **droit du travail algérien**.

> Projet 1 du module RCR | M1-IA | Université Constantine 2 – Abdelhamid Mehri | Prof. BOURAMOUL

## Objectif

Construire un assistant qui répond à des questions sur le droit du travail algérien (loi n° 90-11 du 21 avril 1990) en citant **l'article exact et sa version en vigueur**. Si les textes ne suffisent pas, le système le dit au lieu d'inventer.

## Étapes du projet

1. **Collecte** : récupérer les textes du Journal officiel (PDF) et garder ceux qui concernent le travail.
2. **Structuration** : découper les textes en articles et enregistrer les liens entre textes.
3. **Versions** : suivre les modifications d'un article dans le temps.
4. **Recherche** : retrouver les articles pertinents (BM25 et embeddings, comparés).
5. **Réponse** : générer une réponse avec citations à partir des articles trouvés.
6. **Interface et évaluation** : interface web et jeu de test d'au moins 30 questions.

## Format des réponses

- (a) Réponse courte
- (b) Explication en langage simple
- (c) Articles cités avec leur version
- (d) Niveau de confiance et limites

## Règles

- Le système informe, il ne remplace pas un conseil juridique.
- Aucun article, numéro ou date absent du corpus n'apparaît dans une réponse.
- En cas de contradiction entre deux textes, celui de rang supérieur l'emporte.

## Installation

```bash
git clone https://github.com/rcr-project1/jurideazor.git
cd jurideazor
pip install -r requirements.txt
```

## Modèle de langage et clé API

Selon la consigne mise à jour par l'enseignant, le modèle imposé est
`openai/gpt-oss-120b`, accessible via l'API Groq. Le nom contient `openai/`,
mais les requêtes passent par Groq, pas par l'API OpenAI.

Chaque membre crée sa propre clé gratuite sur
[Groq Console](https://console.groq.com/keys). Ne partagez pas votre clé et
n'ajoutez aucun moyen de paiement.

Pour un développement local, définissez la variable d'environnement
`GROQ_API_KEY`. Si vous utilisez un fichier `.env`, gardez-le uniquement sur
votre machine et ne le poussez jamais sur Git :

```
GROQ_API_KEY=votre_cle_ici
```

Le cahier des charges initial mentionne Gemini ; cette consigne est remplacée
par l'annonce plus récente de l'enseignant. Le modèle de secours
`openai/gpt-oss-20b` ne doit être utilisé que si l'enseignant l'annonce.

## Équipe

[
Haroudi nouha
Aliouat Malak
boukhalfa hadil
benzerafa rania halima
bougoffa malak
]


## Documentation

### 1. Présentation du projet
- [Mission du projet](docs/week1/fixermission.md)

### 2. Cas pratique et questions de test
- [Questions de test](docs/week1/evaluation/question-test.md)

### 3. Évaluation du LLM sans RAG
- [Analyse des réponses d'un LLM sans RAG](docs/week1/evaluation/Analyse%20des%20réponses%20d'un%20LLM%20sans%20RAG)
- [Réponses avec sources et références](docs/week1/evaluation/Réponses%20avec%20sources%20et%20références)
- [Réponses de LLM sans RAG](docs/week1/evaluation/réponses%20de%20LLM%20sans%20RAG)

