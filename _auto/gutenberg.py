#!/usr/bin/env python3
"""
BookClassics — recherche rapide dans le catalogue officiel de Project Gutenberg (pg_catalog.csv).

Pour chaque édition : numéro, langue, titre, auteurs et traducteurs avec leurs dates, et un verdict
« libre UE » : toutes les personnes (auteur ET traducteur) mortes au plus tard en 1955.

Usage :
  python3 gutenberg.py "Doyle" [langue ...]          # éditions dont un auteur contient « Doyle »
  python3 gutenberg.py "Doyle" fr de --titre scarlet  # filtrées sur le titre
  python3 gutenberg.py --num 244 13952                # fiche de numéros précis
"""
import csv, io, os, re, sys, time, urllib.request

URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
CACHE = os.path.expanduser("~/.cache/pg_catalog.csv")
YEAR_LIMIT = 1955
csv.field_size_limit(10**8)


def rows():
    if not os.path.exists(CACHE) or time.time() - os.path.getmtime(CACHE) > 7 * 86400:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "BookClassics/1.0"})
        open(CACHE, "wb").write(urllib.request.urlopen(req, timeout=300).read())
    return list(csv.DictReader(open(CACHE, encoding="utf-8")))


PERSON = re.compile(r"^(?P<name>.*?)(?:,\s*(?P<b>(?:BCE?\s*)?\d{1,4}\??|-?\d+)?\s*-\s*(?P<d>\d{1,4}\??)?(?:\s*BCE?)?)?\s*(?:\[(?P<role>[^\]]+)\])?$")


def people(field):
    out = []
    for part in (field or "").split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.search(r"\[([^\]]+)\]\s*$", part)
        role = m.group(1) if m else "Author"
        core = re.sub(r"\s*\[[^\]]+\]\s*$", "", part)
        dm = re.search(r",\s*(BCE?\s*)?(\d{1,4})?\??\s*(BCE?)?\s*-\s*(\d{1,4})?\??\s*(BCE?)?$", core)
        birth = death = None
        if dm:
            bc = bool(dm.group(1) or dm.group(3))
            birth = int(dm.group(2)) * (-1 if bc else 1) if dm.group(2) else None
            death = int(dm.group(4)) * (-1 if (dm.group(5) or (bc and not dm.group(5) and int(dm.group(4) or 0) < int(dm.group(2) or 0))) else 1) if dm.group(4) else None
            name = core[:dm.start()].strip()
        else:
            name = core.strip()
        out.append({"name": name, "birth": birth, "death": death, "role": role})
    return out


def libre_ue(ps):
    """True si toutes les personnes sont mortes au plus tard en 1955 (ou œuvre très ancienne)."""
    relevant = [p for p in ps if p["role"] in ("Author", "Translator", "Contributor") or True]
    if not relevant:
        return False
    for p in relevant:
        if p["role"] in ("Editor", "Illustrator", "Commentator", "Annotator", "Compiler", "Photographer"):
            continue
        if p["death"] is None:
            if p["birth"] is None or p["birth"] > 1800:
                return False
        elif p["death"] > YEAR_LIMIT:
            return False
    return True


def fmt(r):
    ps = people(r["Authors"])
    who = "; ".join(f"{p['name']} ({p['birth']}-{p['death']})" + ("" if p["role"] == "Author" else f" [{p['role']}]") for p in ps)
    title = " ".join(r["Title"].split())[:110]
    return f"#{r['Text#']:>6} {r['Language']:5} {'LIBRE-UE' if libre_ue(ps) else 'NON-UE  '} {title} — {who}"


def main():
    a = sys.argv[1:]
    data = [r for r in rows() if r["Type"] == "Text"]
    if a and a[0] == "--num":
        nums = set(a[1:])
        for r in data:
            if r["Text#"] in nums:
                print(fmt(r))
        return
    if not a:
        print(__doc__)
        return
    who = a[0].lower()
    titre = None
    if "--titre" in a:
        i = a.index("--titre")
        titre = a[i + 1].lower()
        a = a[:i] + a[i + 2:]
    langs = set(a[1:])
    for r in data:
        if who not in r["Authors"].lower():
            continue
        if langs and r["Language"] not in langs:
            continue
        if titre and titre not in r["Title"].lower():
            continue
        print(fmt(r))


if __name__ == "__main__":
    main()
