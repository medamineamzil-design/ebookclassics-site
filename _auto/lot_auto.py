#!/usr/bin/env python3
"""
BookClassics — lot AUTOMATIQUE (sans Claude), pour les livres au-delà des grands classiques.

Choisit les livres anglais les plus téléchargés de Project Gutenberg qui ne sont ni publiés, ni refusés,
ni réservés à l'agent (file_attente.json), vérifie le domaine public (auteur ET traducteur morts au plus
tard en 1955, d'après le catalogue officiel), puis rédige la fiche à partir de Wikipédia (anglais) :
résumé, pays et année (Wikidata), biographie de l'auteur. Le texte repris de Wikipédia est crédité
(licence CC BY-SA 4.0) dans un paragraphe dédié. Un livre sans article Wikipédia sûr est sauté.

Usage : python3 lot_auto.py <nombre> <sortie.json> [--dejapris lot1.json lot2.json ...]
"""
import csv, html, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gutenberg as G

UA = {"User-Agent": "BookClassics/1.0 (https://bookclassics.org; contact@bookclassics.org)"}
MAN = "https://raw.githubusercontent.com/medamineamzil-design/ebookclassics-files/main/manifest.json"
SKIP = re.compile(r"\b(vol(ume)?\.?\s*[ivx\d]+|part\s+[ivx\d]+|book\s+[ivx\d]+\b|complete works|collected works|"
                  r"works of|index of|magazine|journal|punch|bulletin|dictionary|encyclop|cook|recipes|catalog|"
                  r"bible|handbook|manual|grammar|history of the|letters|memoirs of|report|speeches|essays of|"
                  r"anthology|selections|poems of|sonnets|hymns|songs|state of the union|constitution|"
                  r"declaration|treaty|census|statute|guide|lessons|primer|reader)\b", re.I)
BOOKWORDS = re.compile(r"\b(novel|novella|play|tragedy|comedy|drama|book|poem|epic|story|stories|treatise|"
                       r"essay|fairy tale|fable|satire|romance|tale|tales|memoir|autobiography|dialogue|work)\b", re.I)


def get(url, tries=4, js=True):
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            return json.loads(r) if js else r.decode("utf-8", "replace")
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in s if not unicodedata.combining(c)).lower())


def slug_of(t):
    s = unicodedata.normalize("NFD", t)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60].lower()


def short_title(t):
    t = re.split(r"[:;]|, or,|\bor,|\n", t)[0].strip()
    return re.sub(r"\s+", " ", t)


def popular_ids(pages):
    ids = []
    for p in range(pages):
        h = get(f"https://www.gutenberg.org/ebooks/search/?query=l.en&sort_order=downloads&start_index={1 + 25 * p}", js=False)
        if not h:
            continue
        for m in re.finditer(r'href="/ebooks/(\d+)"', h):
            n = int(m.group(1))
            if n not in ids:
                ids.append(n)
        time.sleep(1)
    return ids


def category(subjects, shelves, wd_genres):
    s = " ".join([subjects, wd_genres]).lower()
    if re.search(r"juvenile|children's|fairy tales|nursery", s):
        return "jeunesse"
    if re.search(r"\bdrama\b|plays|tragedies|comedies|theater|theatre", s):
        return "theatre"
    if re.search(r"adventure|sea stories|western|voyages|explor|war stories|science fiction|detective|mystery", s):
        return "aventure"
    if "fiction" in s or "novel" in s:
        return "fiction"
    if re.search(r"philosoph|ethics|political science|economics|religion|psychology|essays", s):
        return "philosophie"
    return "fiction"


# ------------------------------------------------------------------ Wikipédia / Wikidata
def wiki_search(q, n=5):
    d = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": q, "srlimit": n, "format": "json"}))
    return [x["title"] for x in (d or {}).get("query", {}).get("search", [])]


def wiki_page(title):
    d = get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "extracts|pageprops|description", "exintro": 1, "explaintext": 1,
         "redirects": 1, "titles": title, "format": "json"}))
    for p in (d or {}).get("query", {}).get("pages", {}).values():
        if "missing" in p or "disambiguation" in p.get("pageprops", {}):
            return None
        return {"title": p["title"], "extract": p.get("extract", ""), "qid": p.get("pageprops", {}).get("wikibase_item"),
                "desc": p.get("description", "")}
    return None


def wd_entity(qid):
    d = get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    return (d or {}).get("entities", {}).get(qid) if d else None


def wd_label(qid, cache={}):
    if qid not in cache:
        e = wd_entity(qid)
        cache[qid] = ((e or {}).get("labels", {}).get("en") or {}).get("value", "")
    return cache[qid]


def claims(e, p):
    out = []
    for c in (e or {}).get("claims", {}).get(p, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if v is not None:
            out.append(v)
    return out


def year_of(e):
    ys = []
    for v in claims(e, "P577"):
        m = re.match(r"([+-]\d+)-", v.get("time", ""))
        if m:
            ys.append(int(m.group(1)))
    return min(ys) if ys else None


def paragraphs(extract):
    ps = [re.sub(r"\s+", " ", p).strip() for p in extract.split("\n")]
    return [p for p in ps if len(p) > 60]


def first_sentence(t, maxlen=220):
    s = re.split(r"(?<=[.!?])\s+(?=[A-Z])", t.strip())[0]
    s = re.sub(r"\s*\([^)]*\)", "", s)          # retire les parenthèses (prononciation, dates)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > maxlen:
        s = s[:maxlen - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return s


def credit(page_title):
    url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(page_title.replace(" ", "_"))
    return (f"This description is adapted from the Wikipedia article “{page_title}” ({url}), "
            f"available under the Creative Commons Attribution-ShareAlike 4.0 License.")


def find_book_article(title, author_last):
    tn = set(norm(title).split()) - {"the", "a", "an", "of", "and"}
    for q in (f"{title} {author_last}", f"{title} novel", title):
        for cand in wiki_search(q):
            cn = set(norm(re.sub(r"\(.*?\)", "", cand)).split()) - {"the", "a", "an", "of", "and"}
            if not tn or len(tn & cn) < max(1, int(len(tn) * 0.6)):
                continue
            p = wiki_page(cand)
            if not p or not p["extract"]:
                continue
            head = p["extract"][:600]
            if author_last.lower() in norm(head) and BOOKWORDS.search(head + " " + p["desc"]):
                return p
            time.sleep(0.3)
    return None


def find_author_article(name):
    for cand in wiki_search(name, 3):
        p = wiki_page(cand)
        if p and p["extract"] and name.split()[-1].lower() in norm(p["extract"][:300]):
            return p
    return None


def display_name(n):
    """« Austen, Jane » -> « Jane Austen »."""
    n = re.sub(r"\s*\(.*?\)", "", n)
    if "," in n:
        last, first = n.split(",", 1)
        return f"{first.strip()} {last.strip()}".strip()
    return n.strip()


def main():
    nb, out = int(sys.argv[1]), sys.argv[2]
    deja = sys.argv[sys.argv.index("--dejapris") + 1:] if "--dejapris" in sys.argv else []
    have = set((get(MAN) or {}).get("books", {}))
    have |= {k.rsplit("-", 1)[0] for k in have if re.search(r"-(fr|de|es|it|pt|sv)$", k)}
    have |= {re.sub(r"^(the|a|an)-", "", k) for k in list(have)}
    reserved = set()
    try:
        reserved = {slug_of(b["title"]) for b in json.load(open(os.path.join(HERE, "file_attente.json")))}
    except Exception:
        pass
    refused = set()
    try:
        for x in json.load(open(os.path.join(HERE, "content", "refuses.json"))):
            refused.add(slug_of(x if isinstance(x, str) else x.get("title", "")))
    except Exception:
        pass
    taken = set()
    for f in deja:
        try:
            taken |= {slug_of(b["title"]) for b in json.load(open(f)).get("books", [])}
        except Exception:
            pass
    known_authors = set()
    try:
        known_authors = set(json.load(open(os.path.join(HERE, "content", "authors_all.json"))))
    except Exception:
        pass

    cat = {int(r["Text#"]): r for r in G.rows() if r.get("Text#", "").isdigit()}
    books, skipped, authors_n = [], [], {}
    for gid in popular_ids(40):
        if len(books) >= nb:
            break
        r = cat.get(gid)
        if not r or r.get("Type") != "Text" or r.get("Language") != "en":
            continue
        title = short_title(r["Title"])
        slug = slug_of(title)
        if not title or re.sub(r"^(the|a|an)-", "", slug) in have or slug in have or slug in reserved or slug in refused or slug in taken or SKIP.search(r["Title"]):
            continue
        ps = G.people(r.get("Authors", ""))
        if not ps or not G.libre_ue(ps):
            continue
        auth = [p for p in ps if p["role"] == "Author"] or ps
        if any(p["role"] == "Translator" for p in ps):
            continue                                   # traductions : laissées à l'agent (vérification humaine)
        aname = display_name(auth[0]["name"])
        if not aname or "anonymous" in aname.lower() or "unknown" in aname.lower():
            continue
        if authors_n.get(aname, 0) >= 2:
            continue
        last = norm(aname).split()[-1]
        page = find_book_article(title, last)
        if not page:
            skipped.append(f"{title} (#{gid}) : pas d'article Wikipédia sûr")
            continue
        ent = wd_entity(page["qid"]) if page["qid"] else None
        langs = [v.get("id") for v in claims(ent, "P407") if isinstance(v, dict)]
        if langs and "Q1860" not in langs:
            skipped.append(f"{title} (#{gid}) : œuvre traduite (langue d'origine non anglaise)")
            continue
        check = " ".join([w for w in norm(title).split() if w not in ("the", "a", "an")][:3])
        wt = re.sub(r"\s*\(.*?\)\s*$", "", page["title"]).strip()
        if wt and len(wt) <= 80:
            title = wt
            slug = slug_of(title)
            if slug in have or re.sub(r"^(the|a|an)-", "", slug) in have or slug in reserved or slug in refused or slug in taken or slug in {slug_of(x["title"]) for x in books}:
                continue
        auths = [wd_label(v["id"]) for v in claims(ent, "P50") if isinstance(v, dict) and v.get("id")]
        if len(auths) == 1 and norm(auths[0]).split() and norm(auths[0]).split()[-1] == last:
            aname = auths[0]
        if authors_n.get(aname, 0) >= 2:
            continue
        if re.search(r"mathematic|calculus|science|textbook|cookery|medicine|law\b|grammar|arithmetic", r.get("Subjects", ""), re.I) and "fiction" not in r.get("Subjects", "").lower():
            continue
        year = year_of(ent)
        countries = [wd_label(v["id"]) for v in claims(ent, "P495") if isinstance(v, dict) and v.get("id")][:1]
        genres = " ".join(wd_label(v["id"]) for v in claims(ent, "P136")[:3] if isinstance(v, dict) and v.get("id"))
        if not year:
            skipped.append(f"{title} (#{gid}) : année de publication inconnue (Wikidata)")
            continue
        paras = paragraphs(page["extract"])[:3]
        if not paras:
            continue
        b = {"title": title, "author": aname,
             "cat": category(r.get("Subjects", ""), r.get("Bookshelves", ""), genres),
             "meta": " · ".join([c for c in countries if c] + [str(year)]),
             "desc": first_sentence(paras[0]),
             "editions": [{"lang": "en", "gid": gid, "check": check}],
             "about": paras + [credit(page["title"])],
             "librivox": [], "source": "wikipedia", "wikipedia": page["title"]}
        if aname not in known_authors:
            ap = find_author_article(aname)
            if ap:
                apar = paragraphs(ap["extract"])[:2]
                b["author_short"] = first_sentence(apar[0], 200) if apar else aname
                b["author_long"] = apar + [credit(ap["title"])]
                known_authors.add(aname)
        books.append(b)
        authors_n[aname] = authors_n.get(aname, 0) + 1
        print(f"{len(books):3} {title[:55]:55} {aname[:28]:28} {b['cat']:10} {b['meta']}", file=sys.stderr, flush=True)
        time.sleep(0.5)
    lot = {"lot": os.path.basename(out).replace("lot-", "").replace(".json", ""), "auto": True,
           "books": books, "skipped": skipped}
    json.dump(lot, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(books)} livres, {len(skipped)} sautés -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
