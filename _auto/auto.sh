#!/bin/bash
# BookClassics — publication automatique (lancé chaque jour par la tâche Windows).
# 1) publie, dans l'ordre, chaque lot reçu dans ~/bookclassics-auto/inbox (livres + site)
# 2) ensuite seulement, ajoute les livres audio LibriVox (long) sans bloquer les publications suivantes
A=~/bookclassics-auto
mkdir -p $A/inbox $A/faits $A/erreurs
export PYTHONDONTWRITEBYTECODE=1
exec 9>$A/.verrou
if flock -n 9; then
  cd ~/ebookclassics-site && git pull -q --rebase --autostash || { echo "!! git pull du site impossible"; exit 1; }
  n=0
  for f in $(ls $A/inbox/*.json 2>/dev/null | sort); do
    n=$((n+1))
    if python3 ~/ebookclassics-site/_auto/publier_lot.py "$f"; then mv "$f" $A/faits/; else mv "$f" $A/erreurs/; echo "!! lot en erreur : $(basename $f)"; fi
  done
  [ $n -eq 0 ] && echo "Aucun nouveau lot a publier aujourd'hui."
  flock -u 9
else
  echo "Une publication est deja en cours : les nouveaux lots attendront le prochain passage."
fi
exec 8>$A/.verrou-audio
if flock -n 8; then
  for f in $(ls $A/faits/*.json 2>/dev/null | sort); do
    [ -e "$f.audio" ] && continue
    python3 ~/ebookclassics-site/_auto/publier_lot.py "$f" --audio-seulement && touch "$f.audio"
  done
else
  echo "Livres audio : un ajout est deja en cours."
fi
echo "FIN $(date '+%Y-%m-%d %H:%M')"
