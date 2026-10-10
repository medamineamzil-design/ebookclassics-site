"""
BookClassics — livres arabes du domaine public, depuis ar.wikisource.org.
Une édition de lot de la forme {"lang": "ar", "wikisource": "<titre de la page>", "title": "<titre arabe>"}
est fabriquée ici (EPUB, PDF, TXT, HTML) avec la même mise en forme que les autres livres, en écriture
de droite à gauche. Aucune mention de source dans les livres eux-mêmes.
"""
import base64, html, json, os, re, time, urllib.parse, urllib.request

UA = {"User-Agent": "BookClassicsBot/1.0 (https://bookclassics.org; contact@bookclassics.org)"}
API = "https://ar.wikisource.org/w/api.php?"


def api(**p):
    p["format"] = "json"
    p.setdefault("formatversion", 2)
    last = None
    for i in range(6):
        try:
            req = urllib.request.Request(API + urllib.parse.urlencode(p), headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as ex:
            last = ex
            time.sleep(3 + 6 * i)
    raise RuntimeError(f"Wikisource injoignable : {last}")


def subpages_in_order(title):
    """Sous-pages dans l'ordre où la page d'accueil du livre les cite."""
    d = api(action="parse", page=title, prop="text", redirects=1)["parse"]
    root = d["title"]
    order = []
    for m in re.finditer(r'href="/wiki/([^"#?]+)"', d["text"]):
        t = urllib.parse.unquote(m.group(1)).replace("_", " ")
        if t.startswith(root + "/") and t not in order:
            order.append(t)
    # une page qui a elle-même des sous-pages n'est qu'un sommaire : on la saute
    order = [t for t in order if not any(o.startswith(t + "/") for o in order)]
    return root, order


STRIP = re.compile(r'<(table|div)[^>]*class="[^"]*(header|navbox|ws-noexport|noprint|mw-references|reflist|toc|licen|footer)[^"]*"[\s\S]*?</\1>', re.I)
PAGE_HEAD = re.compile(r"^(صفحة|ص)\s*:?\s*\d+$")


def page_blocks(title):
    t = api(action="parse", page=title, prop="text", redirects=1, disableeditsection=1)["parse"]["text"]
    t = STRIP.sub("", t)
    t = re.sub(r'<sup[^>]*class="reference"[\s\S]*?</sup>', "", t)
    t = re.sub(r"<(style|script)[\s\S]*?</\1>", "", t)
    out = []
    for m in re.finditer(r"<(h[1-6]|p|dd|li|center|poem)[^>]*>([\s\S]*?)</\1>", t):
        tag, inner = m.group(1), m.group(2)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        txt = html.unescape(re.sub(r"<[^>]+>", "", inner))
        txt = re.sub(r"\[\s*\d+\s*\]", "", txt)
        txt = re.sub(r"[ \t ]+", " ", txt)
        txt = re.sub(r"\n\s*\n+", "\n", txt).strip()
        if not txt or txt in ("[عدل]", "عدل"):
            continue
        if txt.count(" | ") >= 2:                    # barre de navigation entre chapitres
            continue
        out.append(("h" if tag.startswith("h") else "p", txt))
    return out


def clean_head(t):
    t = re.sub(r"^فصل\s*:\s*", "", t).strip()
    return t


def book_blocks(title):
    root, subs = subpages_in_order(title)
    if not subs:
        raw = page_blocks(root)
    else:
        raw = []
        for s in subs:
            name = s.split("/")[-1].strip()
            bl = page_blocks(s)
            if not PAGE_HEAD.match(name) and (not bl or bl[0][0] != "h"):
                raw.append(("h", name))
            raw += bl
            time.sleep(0.3)
    blocks, seen = [], set()
    for k, t in raw:
        if k == "h":
            t = clean_head(t)
            if PAGE_HEAD.match(t) or not t:
                continue
            if blocks and blocks[-1][0] == "h":
                blocks[-1] = ("h", t)              # deux titres de suite : on garde le plus précis
                continue
        else:
            key = t[:200]
            if len(t) > 80 and key in seen:         # paragraphe déjà présent (page répétée)
                continue
            seen.add(key)
        blocks.append((k, t))
    while blocks and blocks[-1][0] == "h":
        blocks.pop()
    return blocks


def produce_ar(out_dir, slug, title_ar, author_ar, page, seed, report, credit=""):
    """Fabrique slug-ar.{epub,pdf,txt,html} et la couverture, comme EB.produce pour Gutenberg."""
    import mise_en_forme as MF
    lang = "ar"
    folder = os.path.join(out_dir, slug)
    os.makedirs(folder, exist_ok=True)
    stem = os.path.join(folder, f"{slug}-{lang}")
    if all(os.path.exists(f"{stem}.{e}") for e in ("epub", "pdf", "txt", "html")):
        report.append(f"= {slug} [{lang}] déjà fait (ignoré)")
        return
    blocks = book_blocks(page)
    words = sum(len(t.split()) for _, t in blocks)
    if words < 5000:
        report.append(f"! {slug} [{lang}] : texte trop court ({words} mots, Wikisource « {page} ») — IGNORÉ")
        return
    cover_svg = f"{stem}-cover.svg"
    with open(cover_svg, "w", encoding="utf-8") as f:
        f.write(MF.cover_svg(title_ar, author_ar, seed, lang))
    cover_png = f"{stem}-cover.png"
    MF.svg_to_png(cover_svg, cover_png)
    cover = cover_png if os.path.exists(cover_png) else None
    svg_uri = "data:image/svg+xml;base64," + base64.b64encode(open(cover_svg, "rb").read()).decode()
    with open(f"{stem}.html", "w", encoding="utf-8") as f:
        f.write(MF.build_html(title_ar, author_ar, lang, blocks, credit, svg_uri))
    with open(f"{stem}.txt", "w", encoding="utf-8") as f:
        f.write(MF.build_txt(title_ar, author_ar, lang, blocks, credit))
    epub_src = os.path.join(folder, "_epub_src.html")
    with open(epub_src, "w", encoding="utf-8") as f:
        f.write(MF.build_html(title_ar, author_ar, lang, blocks, credit, None, toc=False))
    ok_epub = MF.make_epub(epub_src, f"{stem}.epub", title_ar, author_ar, lang, cover, folder, credit)
    os.remove(epub_src)
    typ = MF.build_typst(title_ar, author_ar, lang, blocks, credit, os.path.basename(cover) if cover else None)
    ok_pdf = MF.make_pdf(typ, f"{stem}.pdf", folder, f"{stem}.html")
    if os.path.exists(os.path.join(folder, "_epub.css")):
        os.remove(os.path.join(folder, "_epub.css"))
    sizes = " ".join(f"{e}:{os.path.getsize(f'{stem}.{e}') // 1024}Ko" for e in ("epub", "pdf", "txt", "html")
                     if os.path.exists(f"{stem}.{e}"))
    status = "OK" if ok_epub and ok_pdf else "PARTIEL"
    report.append(f"{'+' if status == 'OK' else '~'} {slug} [{lang}] {status} — Wikisource « {page} », "
                  f"{words} mots, {sum(1 for k, _ in blocks if k == 'h')} chapitres — {sizes}")
