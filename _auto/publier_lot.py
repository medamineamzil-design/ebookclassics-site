#!/usr/bin/env python3
"""
BookClassics — publication automatique d'un lot de nouveaux livres (sans IA, sur le PC).

Le lot (fichier JSON préparé chaque jour par l'agent Claude) donne pour chaque livre :
le titre, l'auteur, la catégorie, les éditions Gutenberg (langue, numéro, mots de contrôle,
traducteur), les textes « À propos » et la biographie de l'auteur, et les enregistrements LibriVox.

Étapes (même fabrication que les 126 premiers livres) :
  1. fabrique EPUB, PDF, TXT, HTML + couverture pour chaque édition (ebooks_build + mise_en_forme)
  2. publie les fichiers et manifest.json sur le dépôt des livres
  3. ajoute les livres au catalogue du site, régénère les pages livres et le plan du site, publie
  4. ajoute les livres audio LibriVox (Cloudflare R2), quand ils existent

Un livre déjà présent dans le dépôt n'est jamais modifié. Un livre dont aucune édition
n'est fabriquée correctement n'apparaît pas sur le site.

Usage : python3 publier_lot.py <lot.json> [--sans-push] [--sans-audio]
        python3 publier_lot.py <lot.json> --verifier     (contrôle seulement, ne publie rien)
        (dépôts : ~/ebookclassics-files et ~/ebookclassics-site, ou variables EBC_FILES / EBC_SITE)
"""
import datetime, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jslit  # noqa: E402

FILES = os.environ.get("EBC_FILES", os.path.expanduser("~/ebookclassics-files"))
SITE = os.environ.get("EBC_SITE", os.path.expanduser("~/ebookclassics-site"))
WORK = os.environ.get("EBC_WORK", os.path.expanduser("~/bookclassics-auto/travail"))
CATS = {"fiction", "aventure", "theatre", "philosophie", "jeunesse"}
LANGS = {"en", "fr", "es", "de", "it", "pt", "sv"}
PUSH = "--sans-push" not in sys.argv
AUDIO = "--sans-audio" not in sys.argv
LOG = []


def say(msg):
    print(msg, flush=True)
    LOG.append(msg)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} : {r.stderr.strip()[:300]}")
    return r


def push(repo, msg, paths):
    git(repo, "add", "-A", *paths)
    if git(repo, "commit", "-q", "-m", msg, check=False).returncode:
        say(f"   (rien de nouveau à publier dans {os.path.basename(repo)})")
        return False
    if not PUSH:
        say(f"   commit local (sans push) : {msg}")
        return True
    for _ in range(3):
        if git(repo, "push", "-q", check=False).returncode == 0:
            say(f"   publié : {os.path.basename(repo)} — {msg}")
            return True
        git(repo, "pull", "-q", "--rebase", "--autostash", check=False)
    raise RuntimeError(f"push impossible sur {repo}")


# ------------------------------------------------------------------ contrôle du lot
def check_lot(lot):
    errs, ok = [], []
    for b in lot.get("books", []):
        t = b.get("title", "?")
        e = []
        for k in ("title", "author", "cat", "meta", "desc", "editions", "about"):
            if not b.get(k):
                e.append(f"champ « {k} » manquant")
        if b.get("cat") not in CATS:
            e.append(f"catégorie inconnue « {b.get('cat')} »")
        for ed in b.get("editions", []):
            if ed.get("lang") not in LANGS or not isinstance(ed.get("gid"), int) or not ed.get("check"):
                e.append(f"édition invalide {ed}")
        if b.get("about") and (not isinstance(b["about"], list) or len(b["about"]) < 2):
            e.append("« about » doit contenir au moins 2 paragraphes")
        if e:
            errs.append(f"! {t} : " + " ; ".join(e))
        else:
            ok.append(b)
    return ok, errs


# ------------------------------------------------------------------ 1. fabrication
def build(books, lot_name):
    import ebooks_build as EB
    EB.OUT = os.path.join(WORK, lot_name)
    os.makedirs(EB.OUT, exist_ok=True)
    report = []
    made = {}
    for b in books:
        slug = EB.slug_of(b["title"])
        if os.path.isdir(os.path.join(FILES, slug)):
            say(f"= {b['title']} : déjà dans la bibliothèque — ignoré")
            continue
        seed = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 97
        for ed in b["editions"]:
            say(f"… {b['title']} [{ed['lang']}] — Gutenberg #{ed['gid']}")
            try:
                EB.produce(b["title"], b["author"], ed["lang"], ed["gid"], ed["check"], seed, report,
                           display_title=ed.get("title") or None, credit=ed.get("credit", ""))
            except Exception as ex:
                report.append(f"! {slug} [{ed['lang']}] ERREUR : {ex}")
            say("   " + report[-1])
            time.sleep(1)
        folder = os.path.join(EB.OUT, slug)
        langs = []
        for ed in b["editions"]:
            stem = slug if ed["lang"] == "en" else f"{slug}-{ed['lang']}"
            if all(os.path.exists(os.path.join(folder, f"{stem}.{x}")) and
                   os.path.getsize(os.path.join(folder, f"{stem}.{x}")) > 1000 for x in ("epub", "pdf", "txt", "html")):
                langs.append(ed["lang"])
        # une édition beaucoup plus courte que les autres est une version abrégée : on l'écarte
        if len(langs) > 1:
            wc = {l: words_of(folder, slug, [l]) for l in langs}
            top = max(wc.values())
            for l in list(langs):
                if wc[l] < 0.55 * top:
                    langs.remove(l)
                    say(f"   ! {b['title']} [{l}] : {wc[l]} mots contre {top} — édition abrégée, écartée")
        if langs:
            made[slug] = (b, folder, langs)
    return made


def words_of(folder, slug, langs):
    stem = slug if langs[0] == "en" or ("en" in langs and len(langs) > 1) else f"{slug}-{langs[0]}"
    try:
        return len(open(os.path.join(folder, stem + ".txt"), encoding="utf-8").read().split())
    except Exception:
        return 0


def edition_titles(slug, langs):
    """Titre de chaque édition (1re ligne du TXT publié), comme pour les 126 premiers livres."""
    t = {}
    for lang in langs:
        stem = slug if lang == "en" else f"{slug}-{lang}"
        try:
            t[lang] = open(os.path.join(FILES, slug, stem + ".txt"), encoding="utf-8").readline().strip()[:120]
        except Exception:
            pass
    return t


def cover_jpg(folder, slug, langs):
    """Couverture du site : la couverture de l'édition anglaise (ou de la 1re langue) en JPEG."""
    from PIL import Image
    stem = slug if "en" in langs else f"{slug}-{langs[0]}"
    png = os.path.join(folder, stem + "-cover.png")
    if os.path.exists(png):
        Image.open(png).convert("RGB").save(os.path.join(folder, slug + ".jpg"), "JPEG", quality=88)


# ------------------------------------------------------------------ 3. site
def js(s):
    return json.dumps(s, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def patch_site(index_path, entries):
    site = open(index_path, encoding="utf-8").read()
    books = jslit.const(site, "BOOKS")
    have = {jslit.slug_file(b["title"]) for b in books}
    nums = [int(b["id"][1:]) for b in books if re.match(r"b\d+$", b.get("id", ""))]
    nxt = max(nums) + 1
    a, z = jslit.const_span(site, "BOOKS")
    block = site[a:z]
    add = []
    bios = jslit.const(site, "AUTHOR_BIOS")
    extra = jslit.const(site, "BOOK_EXTRA")
    for b, pages, titles in entries:
        slug = jslit.slug_file(b["title"])
        if slug in have:
            continue
        extra.setdefault(slug, {"t": titles, "o": []})
        hue = int(hashlib.md5(b["title"].encode()).hexdigest(), 16)
        e = (f"  {{id:'b{nxt}', cat:'{b['cat']}', h:[{hue % 360},{(hue // 360) % 360}], coverImg:{js('/covers/' + slug + '.jpg')}, title:{js(b['title'])}, "
             f"author:{js(b['author'])}, meta:{js(b['meta'])}, price:0.99, rating:0, reviews:0, pages:{pages}, "
             f"formats:['EPUB','PDF','TXT','HTML'],\n    desc:{js(b['desc'])}}},")
        add.append(e)
        nxt += 1
        if b.get("author_short") and b["author"] not in bios:
            bios[b["author"]] = b["author_short"]
    if not add:
        return 0
    body = block.rstrip()
    assert body.endswith("]")
    body = body[:-1].rstrip()
    if not body.endswith(","):
        body += ","
    new_block = body + "\n" + "\n".join(add) + "\n]"
    site = site[:a] + new_block + site[z:]
    a, z = jslit.const_span(site, "AUTHOR_BIOS")
    site = site[:a] + json.dumps(bios, ensure_ascii=False) + site[z:]
    a, z = jslit.const_span(site, "BOOK_EXTRA")
    site = site[:a] + json.dumps(extra, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + site[z:]
    # contrôle : les données se relisent correctement
    assert len(jslit.const(site, "BOOKS")) == len(books) + len(add)
    jslit.const(site, "AUTHOR_BIOS")
    assert len(jslit.const(site, "BOOK_EXTRA")) == len(extra)
    open(index_path, "w", encoding="utf-8").write(site)
    return len(add)


def update_content(made):
    cdir = os.path.join(HERE, "content")
    about = json.load(open(os.path.join(cdir, "about_all.json"), encoding="utf-8"))
    auth = json.load(open(os.path.join(cdir, "authors_all.json"), encoding="utf-8"))
    noop = json.load(open(os.path.join(cdir, "no_opening.json"), encoding="utf-8"))
    mk_path = os.path.join(cdir, "markers_auto.json")
    markers = json.load(open(mk_path, encoding="utf-8")) if os.path.exists(mk_path) else {}
    for slug, (b, _, _) in made.items():
        about[slug] = b["about"]
        if b.get("author_long") and b["author"] not in auth:
            auth[b["author"]] = b["author_long"]
        if b.get("no_opening") and slug not in noop:
            noop.append(slug)
        if b.get("marker"):
            markers[slug] = b["marker"]
    for name, obj in (("about_all.json", about), ("authors_all.json", auth), ("no_opening.json", noop),
                      ("markers_auto.json", markers)):
        json.dump(obj, open(os.path.join(cdir, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def rebuild_pages():
    """Pages /books/, /books/<slug>/, couvertures, sitemap.xml, robots.txt — comme à la main."""
    d = jslit.books_json(open(os.path.join(SITE, "index.html"), encoding="utf-8").read())
    json.dump(d, open(os.path.join(HERE, "books.json"), "w"), indent=1, ensure_ascii=False)
    out = os.path.join(WORK, "pages")
    shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_books.py"), os.path.join(SITE, "index.html"), FILES, out],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("build_books : " + r.stderr[-800:])
    say("   " + r.stdout.strip().splitlines()[-1])
    subprocess.run([sys.executable, os.path.join(HERE, "apply_logo.py"), out], check=True, capture_output=True)
    n_old = len(os.listdir(os.path.join(SITE, "books"))) if os.path.isdir(os.path.join(SITE, "books")) else 0
    n_new = len(os.listdir(os.path.join(out, "books")))
    if n_new < n_old:
        raise RuntimeError(f"moins de pages livres qu'avant ({n_new} < {n_old}) : publication annulée")
    for name in ("books", "covers"):
        dst = os.path.join(SITE, name)
        for root, _, files in os.walk(os.path.join(out, name)):
            rel = os.path.relpath(root, out)
            os.makedirs(os.path.join(SITE, rel), exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(SITE, rel, f))
    for f in ("sitemap.xml", "robots.txt"):
        shutil.copy2(os.path.join(out, f), os.path.join(SITE, f))
    rb = os.path.join(SITE, "robots.txt")
    t = open(rb).read()
    if "/_auto/" not in t:
        t = t.replace("User-agent: *\n", "User-agent: *\nDisallow: /_auto/\n", 1)
        open(rb, "w").write(t)


# ------------------------------------------------------------------ 4. audio
LV_LANG = {"en": "English", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
           "pt": "Portuguese", "sv": "Swedish"}


def lv_get(params):
    import urllib.parse, urllib.request
    url = "https://librivox.org/api/feed/audiobooks/?" + urllib.parse.urlencode(dict(params, format="json", extended=1))
    req = urllib.request.Request(url, headers={"User-Agent": "BookClassicsBot/1.0 (https://bookclassics.org)"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=90)).get("books", [])
    except Exception:
        return []


def norm_title(t):
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))
    t = re.sub(r"^(the|a|an|le|la|les|l'|der|die|das|el|los|las|il|lo|i|gli|o|os|as)\s+", "", t.strip().lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def lv_search(title, author, lang):
    """Enregistrement LibriVox complet du livre, dans la bonne langue, du bon auteur (le plus long si plusieurs)."""
    last = norm_title(author.split()[-1]) if author and author != "Anonymous" else ""
    found = []
    for b in lv_get({"title": "^" + re.sub(r"^(The|A|An)\s+", "", title)}):
        if b.get("language") != LV_LANG.get(lang):
            continue
        if norm_title(b.get("title", "")).split(" version")[0].split(" dramatic")[0] != norm_title(title):
            continue
        names = " ".join(f"{a.get('first_name', '')} {a.get('last_name', '')}" for a in b.get("authors", [])).lower()
        if last and last not in norm_title(names):
            continue
        if "abridged" in (b.get("title", "") + b.get("description", "")).lower():
            continue
        if int(b.get("totaltimesecs") or 0) >= 600 and b.get("sections"):
            found.append(b)
    return max(found, key=lambda b: int(b["totaltimesecs"])) if found else None


def audio(made):
    picks = []
    for slug, (b, _, langs) in made.items():
        if b.get("librivox") is False:
            continue
        wanted = b.get("librivox") or [{"lang": l} for l in langs]
        titles = edition_titles(slug, langs)
        for lv in wanted:
            lang = lv.get("lang")
            if lang not in langs:
                continue
            if lv.get("id"):
                got = lv_get({"id": int(lv["id"])})
                data = got[0] if got else None
            else:
                data = lv_search(b["title"] if lang == "en" else titles.get(lang, b["title"]), b["author"], lang)
            if not data:
                say(f"   pas d'enregistrement LibriVox pour {b['title']} [{lang}]")
                continue
            sections = [x["listen_url"] for x in data.get("sections", []) if x.get("listen_url")]
            secs = int(data.get("totaltimesecs") or 0)
            if secs < 600 or not sections:
                continue
            say(f"   LibriVox : {b['title']} [{lang}] — « {data.get('title')} » ({secs // 3600} h {secs % 3600 // 60:02d})")
            picks.append({"slug": slug, "lang": lang, "title": b["title"], "author": b["author"],
                          "lv_id": str(data.get("id")), "lv_title": data.get("title", ""), "secs": secs, "sections": sections})
    if not picks:
        say("   aucun livre audio dans ce lot")
        return
    if not os.path.exists(os.path.expanduser("~/r2.conf")):
        say("   ! ~/r2.conf absent : livres audio non ajoutés")
        return
    miss_path = os.path.join(FILES, "_rapports", "audio-a-synthetiser.txt")
    missing = [l for l in open(miss_path, encoding="utf-8").read().splitlines() if l.strip()] if os.path.exists(miss_path) else []
    plan = os.path.join(WORK, "audio_plan.json")
    json.dump({"picks": picks, "missing": missing}, open(plan, "w"), indent=1)
    import ebooks_audio as EA
    EA.PLAN = plan
    EA.REPO = FILES
    say(f"   {len(picks)} livre(s) audio à ajouter (peut prendre plusieurs heures)")
    EA.main()
    say("   pages livres : ajout des boutons Écouter")
    rebuild_pages()
    push(SITE, "Livres audio : boutons Ecouter des nouveaux livres", ["books", "covers", "sitemap.xml", "robots.txt"])


# ------------------------------------------------------------------ vérification (pour l'agent)
def verifier(lot):
    """Contrôle un lot sans rien publier : champs, catégories, numéros Gutenberg (en-tête et langue)."""
    import ebooks_build as EB
    books, errs = check_lot(lot)
    for e in errs:
        print(e)
    bad = len(errs)
    for b in books:
        for ed in b["editions"]:
            try:
                raw = EB.get_text(ed["gid"])
                ok = EB.header_ok(raw, ed["check"], ed["lang"])
                words = len(EB.strip_gutenberg(raw).split())
                print(f"{'OK ' if ok else 'KO '} {b['title']} [{ed['lang']}] #{ed['gid']} — « {EB.header_title(raw)[:70]} » — {words} mots")
                bad += 0 if ok else 1
            except Exception as ex:
                print(f"KO  {b['title']} [{ed['lang']}] #{ed['gid']} — {ex}")
                bad += 1
    print("LOT VALIDE" if bad == 0 else f"LOT A CORRIGER ({bad} probleme(s))")
    return 0 if bad == 0 else 1


# ------------------------------------------------------------------ programme
def main():
    lot_path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    lot = json.load(open(lot_path, encoding="utf-8"))
    if "--verifier" in sys.argv:
        return verifier(lot)
    lot_name = lot.get("lot") or os.path.splitext(os.path.basename(lot_path))[0]
    say(f"=== BookClassics — lot {lot_name} — {datetime.datetime.now():%Y-%m-%d %H:%M} ===")
    books, errs = check_lot(lot)
    for e in errs:
        say(e)
    for repo in (FILES, SITE):
        git(repo, "pull", "-q", "--rebase", "--autostash")

    if lot.get("refused"):
        rp = os.path.join(HERE, "content", "refuses.json")
        ref = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else []
        known = {r.get("title") for r in ref}
        ref += [r for r in lot["refused"] if r.get("title") not in known]
        json.dump(ref, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        say(f"   {len(lot['refused'])} livre(s) écarté(s) par l'agent, notés dans refuses.json")

    say("== 1/4 Fabrication des livres (EPUB, PDF, TXT, HTML) ==")
    made = build(books, lot_name)
    if not made:
        say("Aucun nouveau livre fabriqué : rien à publier.")
        if lot.get("refused"):
            push(SITE, "Agent : livres ecartes", ["_auto"])
        return 0

    say("== 2/4 Dépôt des livres ==")
    for slug, (b, folder, langs) in made.items():
        cover_jpg(folder, slug, langs)
        dst = os.path.join(FILES, slug)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(folder):
            if f.startswith("_"):
                continue
            m = re.match(re.escape(slug) + r"(?:-([a-z]{2}))?(?:-cover)?\.(epub|pdf|txt|html|png|svg|jpg)$", f)
            if f == slug + ".jpg" or (m and (m.group(1) or "en") in langs):
                shutil.copy2(os.path.join(folder, f), os.path.join(dst, f))
        say(f"+ {b['title']} : {', '.join(langs)}")
    subprocess.run([sys.executable, os.path.join(HERE, "gen_manifest.py"), FILES], check=True, capture_output=True)
    man = json.load(open(os.path.join(FILES, "manifest.json")))["books"]
    made = {s: v for s, v in made.items() if s in man}
    titles = ", ".join(v[0]["title"] for v in made.values())
    push(FILES, f"Nouveaux livres : {titles}", ["."])

    say("== 3/4 Site : catalogue, pages livres, plan du site ==")
    entries = [(b, max(20, round(words_of(folder, slug, langs) / 275)), edition_titles(slug, langs))
               for slug, (b, folder, langs) in made.items()]
    n = patch_site(os.path.join(SITE, "index.html"), entries)
    update_content(made)
    rebuild_pages()
    say(f"   {n} livre(s) ajouté(s) au catalogue")
    dst_auto = os.path.join(SITE, "_auto")
    if os.path.realpath(dst_auto) != os.path.realpath(HERE):
        shutil.copytree(os.path.join(HERE, "content"), os.path.join(dst_auto, "content"), dirs_exist_ok=True)
    push(SITE, f"Nouveaux livres au catalogue : {titles}",
         ["index.html", "books", "covers", "sitemap.xml", "robots.txt", "_auto"])

    if AUDIO:
        say("== 4/4 Livres audio LibriVox ==")
        try:
            audio(made)
        except Exception as ex:
            say(f"   ! audio : {ex}")
    say(f"TERMINE — {len(made)} nouveau(x) livre(s) : {titles}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as ex:
        say(f"!! ERREUR : {ex}")
        code = 1
    rp = os.path.join(WORK, "derniers_rapports")
    os.makedirs(rp, exist_ok=True)
    open(os.path.join(rp, time.strftime("%Y-%m-%d_%H%M") + ".txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    sys.exit(code)
