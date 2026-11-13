# Rapport de correction : Découpage de la Loi 90-11

**Fichier concerné :** `src/structure/split_loi_90_11.py`  
**Statut :** Corrigé et validé

## 1. Objectif
Le script nettoie le texte brut de la **loi 90-11** (version WIPO 1997) et le découpe automatiquement en 158 articles pour créer notre base de données (`articles.json`).

## 2. Problème identifié
Le fichier PDF d'origine contient des erreurs de mise en page. Des débuts d'articles "fantômes" (ex: `Art. 9-`) apparaissaient au milieu du texte de certains articles. 

**Conséquence :** Le script supprimait toute la ligne, ce qui **coupait le texte** des articles 7, 31, 70 et 73. 
*Exemple (Article 7) :* `... mise en place par l’employeur, ganisation et la productivité...` (mot coupé et phrase incomplète).

## 3. Solution apportée
Nous avons modifié la logique du script : au lieu de supprimer la ligne entière, le script **ignore le faux en-tête** mais **conserve le texte qui suit** et l'ajoute à l'article en cours.

**Extrait du code corrigé :**
```python
    # --- FIX: garder le texte après un faux début d'article ---
    if p and i not in acc:
        if cur and p[2]: 
            cur["lines"].append(p[2])
        continue

    4. Résultats
172 articles extraits (158 numéros distincts, 0 manquant).

Le texte des articles 7, 31, 70 et 73 est désormais complet et sans coupure.

14 articles avec suffixe (bis, ter) et 6 extraits de la Constitution correctement identifiés.

5. Code complet corrigé
(Le code complet est disponible dans le fichier src/structure/split_loi_90_11.py sur le dépôt Git).
