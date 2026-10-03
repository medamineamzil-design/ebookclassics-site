#!/bin/bash
# BookClassics — publication automatique (lancé chaque jour par la tâche Windows).
# Publie, dans l'ordre, chaque lot reçu dans ~/bookclassics-auto/inbox.
A=~/bookclassics-auto
mkdir -p $A/inbox $A/faits $A/erreurs
exec 9>$A/.verrou
if ! flock -n 9; then echo "Une publication est deja en cours (livres audio ?) : les lots attendront demain."; exit 0; fi
cd ~/ebookclassics-site && git pull -q --rebase --autostash || { echo "!! git pull du site impossible"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
n=0
for f in $(ls $A/inbox/*.json 2>/dev/null | sort); do
  n=$((n+1))
  if python3 ~/ebookclassics-site/_auto/publier_lot.py "$f"; then mv "$f" $A/faits/; else mv "$f" $A/erreurs/; echo "!! lot en erreur : $(basename $f)"; fi
done
[ $n -eq 0 ] && echo "Aucun nouveau lot a publier aujourd'hui."
echo "FIN $(date '+%Y-%m-%d %H:%M')"
