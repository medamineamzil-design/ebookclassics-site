# Format d'un lot de nouveaux livres (lot-AAAA-MM-JJ.json)

Un lot est un fichier JSON déposé dans `Téléchargements\bookclassics-auto\inbox\`.
La tâche Windows quotidienne le transmet au PC (WSL), puis `publier_lot.py` fabrique et publie tout.

```json
{
 "lot": "2026-10-03",
 "books": [
  {
   "title": "White Fang",                       // titre anglais exact affiché sur le site (sert au slug)
   "author": "Jack London",                     // nom tel qu'affiché (même orthographe que les livres existants)
   "cat": "aventure",                           // fiction | aventure | theatre | philosophie | jeunesse
   "meta": "United States · 1906",              // pays · année de 1re publication
   "desc": "Une phrase d'accroche (anglais, ≤ 220 caractères).",
   "editions": [                                // une entrée par langue ; en, fr, es, de, it, pt, sv
    {"lang": "en", "gid": 910, "check": "white fang"},
    {"lang": "fr", "gid": 65402, "check": "croc blanc",
     "credit": "Traduction : Paul Gruyer (1868-1930), Louis Postif (1887-1942)"},
    {"lang": "de", "gid": 78265, "check": "spate rache", "credit": "anonyme"}
   ],
   "about": ["§1 l'histoire (sans dévoiler la fin)", "§2 thèmes et style", "§3 publication et postérité"],
   "author_short": "Une ligne (nationalité, dates, œuvres) — seulement si l'auteur est nouveau",
   "author_long": ["§1 vie", "§2 œuvre"],         // seulement si l'auteur est nouveau
   "librivox": [],                               // [] = recherche automatique ; false = pas d'audio ;
                                                 // ou [{"lang": "en", "id": 1234}] pour imposer un enregistrement
   "marker": "Début exact du 1er paragraphe",    // facultatif : début de « How it begins »
   "no_opening": false                           // facultatif : true = pas d'extrait « How it begins »
  }
 ],
 "refused": [ {"title": "Heidi", "reason": "traduction anglaise non libre dans l'UE"} ]
}
```

Règles :
- `check` : mots (sans accents) présents dans le titre de l'en-tête Gutenberg de l'édition — contrôle anti-erreur de numéro.
- `credit` : `Traduction : Prénom Nom (naissance-mort), …` pour une traduction ; `anonyme` si le traducteur est inconnu ;
  rien pour une œuvre dans sa langue d'origine. Le libellé est traduit automatiquement dans la langue du livre.
- Domaine public : auteur ET traducteur morts au plus tard en 1955 (UE, valable en 2026) ; traduction anonyme publiée avant 1956.
- Jamais de traduction faite par une IA, jamais d'édition abrégée (écartée automatiquement si < 55 % des mots de la plus longue).
- Un livre déjà présent dans le dépôt n'est jamais modifié.
