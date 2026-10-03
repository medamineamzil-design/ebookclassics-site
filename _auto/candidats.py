#!/usr/bin/env python3
"""
BookClassics — liste de livres candidats pour l'agent (aucune décision automatique).

Parcourt les livres les plus téléchargés de Project Gutenberg (gutendex), écarte ceux déjà
publiés ou déjà refusés, et ne garde que les œuvres libres de droits aux États-Unis ET dans
l'Union européenne : auteur(s) et traducteur(s) morts avant le 1er janvier 1956
(règle des 70 ans, valable jusqu'au 31/12/2026), ou œuvre antique / anonyme ancienne.

Pour chaque candidat : numéro Gutenberg, auteur, dates, nombre de téléchargements, et les
autres éditions trouvées sur Gutenberg (fr, de, es, it, pt, sv) du même auteur.
L'agent vérifie ensuite chaque candidat (titre exact, édition complète, traduction libre de droits).

Usage : python3 candidats.py [nombre=40] [refuses.json] [--langues]
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request

YEAR_LIMIT = 1955          # mort au plus tard en 1955 -> domaine public UE en 2026
MAN = "https://raw.githubusercontent.com/medamineamzil-design/ebookclassics-files/main/manifest.json"
LANGS = ["fr", "de", "es", "it", "pt", "sv"]
SKIP_WORDS = re.compile(r"\b(vol(ume)?\.?\s*[ivx\d]+|part\s+[ivx\d]+|complete works|collected works|\(complete\)|works of|"
                        r"index of|magazine|journal|punch|bulletin|dictionary|encyclop|cook|recipes|catalog|"
                        r"bible|handbook|manual|grammar|history of the|letters of|memoirs of|report)\b", re.I)


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BookClassics-candidats/1.0"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def slug_of(title):
    s = unicodedata.normalize("NFD", title)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60].lower()


def short_title(t):
    return re.split(r"[:;]|, or,|\bor,", t)[0].strip()


def pd_ok(people):
    for p in people:
        d, b = p.get("death_year"), p.get("birth_year")
        if d is None:
            if b is None or b > 1800:
                return False
        elif d > YEAR_LIMIT:
            return False
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 40
    refused = set()
    if len(args) > 1:
        try:
            refused = {slug_of(x if isinstance(x, str) else x.get("title", "")) for x in json.load(open(args[1]))}
        except Exception:
            pass
    have = set((get(MAN) or {}).get("books", {}))
    out, seen, page = [], set(), 1
    while len(out) < n and page <= 40:
        d = get(f"https://gutendex.com/books/?languages=en&sort=popular&page={page}")
        page += 1
        if not d:
            break
        for b in d["results"]:
            title = short_title(b["title"])
            slug = slug_of(title)
            if slug in have or slug in refused or slug in seen or SKIP_WORDS.search(b["title"]):
                continue
            if not b["authors"] or not pd_ok(b["authors"]) or not pd_ok(b.get("translators", [])):
                continue
            if b.get("copyright"):
                continue
            seen.add(slug)
            a = b["authors"][0]
            eds = []
            last = a["name"].split(",")[0]
            for lang in (LANGS if "--langues" in sys.argv else []):
                r = get(f"https://gutendex.com/books/?languages={lang}&search={urllib.parse.quote(last)}")
                for x in (r or {}).get("results", [])[:12]:
                    if any(last.lower() in y["name"].lower() for y in x["authors"]) and pd_ok(x.get("translators", [])):
                        eds.append({"lang": lang, "gid": x["id"], "title": short_title(x["title"]),
                                    "translators": [(t["name"], t["death_year"]) for t in x.get("translators", [])]})
            out.append({"slug": slug, "title": title, "gid": b["id"], "author": a["name"],
                        "dates": [a.get("birth_year"), a.get("death_year")], "downloads": b["download_count"],
                        "subjects": b.get("subjects", [])[:4], "other_language_editions_same_author": eds})
            print(f"{len(out):3} {title[:60]:60} {a['name'][:30]:30} #{b['id']} ({len(eds)} éd. autres langues)",
                  file=sys.stderr, flush=True)
            if len(out) >= n:
                break
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
