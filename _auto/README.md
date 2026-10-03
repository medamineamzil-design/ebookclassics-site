# BookClassics — outils de publication automatique

Ce dossier n'est pas une page du site : il contient les outils qui ajoutent chaque jour de nouveaux livres.

- `publier_lot.py` : publie un lot (JSON préparé par l'agent) : fabrication EPUB/PDF/TXT/HTML,
  dépôt des fichiers, catalogue du site, pages livres, plan du site, livres audio LibriVox.
- `auto.sh` : lancé chaque jour sur le PC par la tâche Windows « BookClassics », publie les lots reçus.
- `content/` : textes des pages livres (À propos du livre, de l'auteur).

Format d'un lot : voir `LOT_FORMAT.md`.
