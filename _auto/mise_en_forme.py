"""
EbookClassics — mise en forme moderne commune à tous les livres.
  - nettoyage de la structure (pages de titre d'origine, sommaires, titres de chapitres fusionnés)
  - HTML de lecture moderne (colonne confortable, sommaire cliquable, mode sombre)
  - EPUB avec couverture PNG, page de titre et sommaire
  - PDF typographié par Typst (format livre 6 x 9 po, en-têtes, numéros de page, chapitres sur page neuve)
  - couverture moderne (SVG + PNG)
Aucune mention de source dans les livres : seulement l'auteur, le traducteur éventuel et la marque.
"""
import html, os, re, shutil, subprocess

LABELS = {
    "en": ("Contents", "Translated by", "Anonymous translation", "BookClassics digital edition", "Public domain text."),
    "fr": ("Table des matières", "Traduction de", "Traduction anonyme", "Édition numérique BookClassics", "Texte du domaine public."),
    "de": ("Inhalt", "Übersetzt von", "Anonyme Übersetzung", "Digitale Ausgabe BookClassics", "Gemeinfreier Text."),
    "es": ("Índice", "Traducción de", "Traducción anónima", "Edición digital BookClassics", "Texto de dominio público."),
    "it": ("Indice", "Traduzione di", "Traduzione anonima", "Edizione digitale BookClassics", "Testo di pubblico dominio."),
    "pt": ("Índice", "Tradução de", "Tradução anónima", "Edição digital BookClassics", "Texto em domínio público."),
    "sv": ("Innehåll", "Översättning av", "Anonym översättning", "Digital utgåva BookClassics", "Fri text (public domain)."),
    "ar": ("المحتويات", "ترجمة", "ترجمة مجهولة", "النسخة الرقمية من BookClassics", "نص في الملك العام."),
}
RTL = {"ar"}
AR_CSS = """
body{font-family:"Amiri","Noto Naskh Arabic","Scheherazade New","Traditional Arabic",serif;font-size:1.3rem;line-height:1.95}
p{text-indent:0;margin:0 0 .7em}
.author{font-style:normal}
h2.chapter + p::first-letter{float:none;font-size:inherit;padding:0;color:inherit}
nav.toc h2{text-align:right;letter-spacing:0}
"""
def labels(lang):
    return LABELS.get(lang, LABELS["en"])

def translator_line(credit, lang):
    """'Traduction : A (1850-1920), B' -> 'Translated by A, B' dans la langue du livre."""
    if not credit:
        return ""
    lab = labels(lang)
    m = re.match(r"^Traduction\s*:\s*(.+)$", credit)
    if m:
        names = re.sub(r"\s*\([^)]*\)", "", m.group(1))
        names = re.sub(r",?\s*(d'après|édition de|2 volumes).*$", "", names).strip(" ,.")
        return f"{lab[1]} {names}"
    return lab[2]

PROPER = set()   # noms propres repérés dans le texte (pour les titres en capitales)
ROMAN = re.compile(r"^(?!(?:IL|DI|MI|CI|LI)$)(C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})[.:]?$")
def nice_case(t, lang="en"):
    """TITRES EN CAPITALES -> Titres En Capitales (en gardant les chiffres romains)."""
    t = re.sub(r"\[\d+\]|\(\d+\)", "", t).strip()       # appels de note dans les titres
    if not t.isupper():
        # « CHAPITRE IV. Comment… » : seul le mot-clé est en capitales
        return re.sub(r"^([A-ZÀ-Ý]{4,})(?=\s)", lambda m: m.group(1).capitalize(), t)
    small = {"of", "the", "and", "a", "an", "in", "to", "de", "la", "le", "les", "du", "des", "et", "der", "die", "das", "und", "von", "del", "di", "e", "y", "el"}
    words = t.lower().split()
    if len(words) == 1 and ROMAN.match(words[0].strip(".:").upper()):
        return t                                      # « VI » seul reste « VI » (pas « Vi »)
    out = []
    if lang != "en":                                  # français, allemand, etc. : casse de phrase
        cap_next = True
        for w in words:
            core = w.strip(".:,;—-()«»“”")
            if core and ROMAN.match(core.upper()) and len(core) <= 6 and core.upper() not in ("DI", "IL", "MI", "CI", "LI", "VI") or core.upper() in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X") and out and re.match(r"^(chapitre|chapter|capitolo|kapitel|capítulo|livre|book|parte|partie|teil|buch|libro|acte|atto|canto|chant)$", out[-1].lower()):
                out.append(w.upper())
            elif cap_next or core in PROPER:
                out.append(w[:1].upper() + w[1:])
            else:
                out.append(w)
            cap_next = bool(re.search(r"[.:!?—]$", w)) or bool(core and ROMAN.match(core.upper()) and out[-1].isupper()) \
                or core in ("premier", "première", "first", "erstes", "erster", "primo", "primero", "primera", "prologue", "prolog")
        res = " ".join(out)
        if lang == "de":                              # en allemand, les noms gardent leur majuscule : on garde l'original en casse titre
            res = " ".join(x[:1].upper() + x[1:] if len(x) > 3 else x for x in res.split())
        return res
    for i, w in enumerate(words):
        after_punct = i > 0 and re.search(r"[.:—\-!?]$", words[i - 1])
        if w.strip(".:,") and ROMAN.match(w.upper().strip(".:,")):
            out.append(w.upper())
        elif i > 0 and w in small and not after_punct:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)

CHAPWORD = re.compile(r"\b(chapter|chapitre|kapitel|capitolo|capítulo|book|livre|buch|libro|part|partie|teil|parte|act|acte|aufzug|stave|canto|chant|scene|scène|szene)\b", re.I)

def is_toc_para(t):
    """Paragraphe qui n'est qu'un ancien sommaire (plusieurs « Chapter … » à la suite)."""
    w = len(t.split())
    if w > 400:
        return False
    hits = len(CHAPWORD.findall(t)) + len(re.findall(r"(?:^|\s)[IVXLC]+\.\s", t))
    return hits >= 3 and hits * 12 >= w

NOTE_HEAD = re.compile(r"^(original\s+)?transcriber[’']?s?\s+notes?(\s+on\s+the\s+text)?\s*:?$|^notes? du transcripteur\s*:?$", re.I)
NOTE_PARA = re.compile(r"project gutenberg|\betexts?\b|\be-text\b|added by this transcriber|this version of the book|"
                       r"html (document|version)|printer[’']s errors have been corrected|obvious (printer|typographical)", re.I)

def drop_notes(blocks):
    """Retire les notes des transcripteurs (section « Transcriber's Notes », remarques en fin de livre,
    [Transcriber's Note: …] dans le texte) et les paragraphes qui parlent de Project Gutenberg."""
    out, skip, n = [], False, len(blocks)
    toc_tail = False
    for i, (k, t) in enumerate(blocks):
        s = t.strip()
        # sommaire placé en fin de livre (Wikisource) : on saute le titre et les lignes courtes qui suivent
        if i > n * 0.5 and re.match(r"^(table des matières|table|contents|inhaltsverzeichnis|indice|índice)\.?$|^\(ne fait pas partie de l[’']ouvrage original\)$", s, re.I):
            toc_tail = True
            continue
        if toc_tail:
            navline = re.match(r"^((?i:chapitre|chapter|capitolo|kapitel|livre|book|partie|part|teil)\s+)?[IVXLC\d]+\.?$|"
                               r"^(?i:premi[eè]re|deuxi[eè]me|troisi[eè]me|first|second|third)\s+(?i:partie|part)\.?$", s)
            if navline or (k == "p" and len(s.split()) < 12):
                continue
            toc_tail = False
        if NOTE_HEAD.match(s):
            skip = True
            continue
        if skip:
            if k == "h":
                skip = False
            else:
                continue
        if k == "p" and len(s) < 1500 and NOTE_PARA.search(s):
            continue
        t = re.sub(r"\s*\[Transcriber[’']?s? [Nn]ote:[^\]]*\]", "", t)
        out.append((k, t))
    return out

def tidy(blocks, head_re, lang="en"):
    """Retire les pages de titre / sommaires d'origine et fusionne les titres consécutifs."""
    from collections import Counter
    import statistics
    blocks = drop_notes(blocks)
    # anciens sommaires avec numéros de page (« VI. ON FOREIGN TRADE      146 ») au début du livre
    lim = int(len(blocks) * 0.15)
    blocks = [b for i, b in enumerate(blocks) if not (i < lim and len(b[1]) < 200 and re.search(r"\S\s{3,}\d{1,4}\s*$", b[1]))]
    caps, lows = Counter(), Counter()
    for k, t in blocks[:4000]:
        if k == "p":
            ws = t.split()
            for a, b in zip(ws, ws[1:]):
                w = b.strip(".,;:!?«»“”\"'()—-")
                if len(w) > 2 and not a.endswith((".", "!", "?", "»", "”", ":")):
                    (caps if w[:1].isupper() and not w.isupper() else lows)[w.lower()] += 1
    PROPER.clear()
    PROPER.update(w for w, c in caps.items() if c >= 3 and c > 3 * lows.get(w, 0))
    # 0) anciens sommaires : entrées du début qui reviennent plus loin (titres ou lignes courtes),
    #    retirées seulement quand elles forment un bloc serré (jamais un vrai titre isolé)
    def nz(x):
        return re.sub(r"[^\w]+", " ", x.lower()).strip()
    n = len(blocks)
    early = int(n * 0.25)
    later = {}
    for idx, (k, t) in enumerate(blocks):
        if len(t.split()) <= 40:
            later.setdefault(nz(t), []).append(idx)
    heads_list = [h for h, ix in later.items() if len(h) >= 6 and any(blocks[j][0] == "h" for j in ix)]
    cand = set()
    for idx in range(early):
        k, t = blocks[idx]
        key = nz(t)
        if len(t.split()) <= 40 and any(j > idx + 10 for j in later.get(key, [])):
            cand.add(idx)
        elif k == "p" and len(t.split()) <= 400:
            hits = sum(1 for h in heads_list if h in key and any(j > idx + 10 for j in later[h]))
            if hits >= 2 and hits * 20 >= len(t.split()):
                cand.add(idx)
    drop = {i for i in cand if sum(1 for j in range(i - 3, i + 4) if j in cand) >= 3}
    blocks = [b for idx, b in enumerate(blocks) if idx not in drop]
    # 1) anciens sommaires : suites d'au moins 5 titres courts, ou paragraphes-sommaires
    cleaned, i, n = [], 0, len(blocks)
    while i < n:
        j = i
        while j < n and len(blocks[j][1].split()) <= 15 and (blocks[j][0] == "h" or head_re.search(blocks[j][1])):
            j += 1
        if j - i >= 5 and i < n * 0.2:
            i = j
            continue
        if blocks[i][0] == "p" and i < n * 0.2 and is_toc_para(blocks[i][1]):
            i += 1
            continue
        cleaned.append(blocks[i]); i += 1
    blocks, n = cleaned, len(cleaned)
    # 2) début réel : 1er titre de chapitre suivi (à 3 blocs près) d'un vrai paragraphe
    start = 0
    for i in range(min(n, 600)):
        k, t = blocks[i]
        if k == "h" and head_re.search(t):
            nxt = blocks[i + 1:i + 4]
            if sum(1 for x in nxt if x[0] == "h") <= 1 and any(x[0] == "p" and len(x[1].split()) >= 40 for x in nxt):
                start = i
                break
    # 3) avant le début : on garde les vrais paragraphes (préface, avis) et leurs titres
    front, kept = blocks[:start], []
    if sum(len(t.split()) for _, t in front) > 3000:
        start, front = 0, []          # prudence : trop de texte avant, on ne retire rien
    for j, (k, t) in enumerate(front):
        nxt = front[j + 1] if j + 1 < len(front) else blocks[start]
        if k == "p" and len(t.split()) >= 40:
            kept.append((k, t))
        elif k == "h" and nxt[0] == "p" and len(nxt[1].split()) >= 40 \
                and not re.search(r"contents|table des mati|inhalt|índice|indice|sommaire", t, re.I):
            kept.append((k, t))
    blocks = kept + blocks[start:]
    # 3b) un « titre » qui revient 4 fois ou plus sans être un vrai titre (Acte, Scène, Chapitre, chiffre romain)
    #     est un nom de personnage (théâtre) ou une signature : il reste dans le texte, sans saut de page
    real = re.compile(r"^(?i:chapter|chapitre|kapitel|capitolo|capítulo|cap[ií]tulo|book|livre|buch|libro|part|partie|teil|parte|"
                      r"volume|tome|act|acte|aufzug|atto|akt|jornada|canto|chant|gesang|stave|canzone|giornata|novella|"
                      r"scene|scène|szene|scena|escena|cena|story|letter|lettre|brief|essay|fable|chapter)\b"
                      r"|^[IVXLC]+[.:]?(\s|$)|^\d{1,3}[.:]?(\s|$)|(?i:erste|zweite|dritte|vierte|fünfte|sechste|siebente|achte)")
    rep = Counter(t.rstrip(".: ").lower() for k, t in blocks if k == "h")
    blocks = [("p" if k == "h" and rep[t.rstrip(".: ").lower()] >= 4 and not real.search(t) else k, t) for k, t in blocks]
    # 4) titres consécutifs : "CHAPITRE I" + "LE DÉPART" -> "Chapitre I — Le départ"
    out = []
    for k, t in blocks:
        if k == "h" and re.match(r"^[“\"'‘«(\[—-]", t) and not head_re.search(t.strip("“\"'‘«»”(")):
            k = "p"   # citation en capitales prise à tort pour un titre
        t = nice_case(t, lang) if k == "h" else t
        if k == "h" and out and out[-1][0] == "h" and t.rstrip(". ").lower() == out[-1][1].rstrip(". ").lower():
            continue
        if k == "h" and out and out[-1][0] == "h" and len(out[-1][1]) < 60 and len(t) < 80 and "—" not in out[-1][1]:
            out[-1] = ("h", f"{out[-1][1].rstrip('.:')} — {t}")
        else:
            out.append((k, t))
    # titres identiques répétés à quelques blocs d'intervalle : on n'en garde qu'un
    dedup = []
    for k, t in out:
        if k in ("h", "s") and any(k2 in ("h", "s") and t2.rstrip(". ").lower() == t.rstrip(". ").lower() for k2, t2 in dedup[-3:]):
            continue
        dedup.append((k, t))
    out = dedup
    # 5) « THE END » / « FIN » : tout ce qui suit (catalogues d'éditeur, publicités) est retiré
    for i in range(len(out) - 1, max(-1, int(len(out) * 0.9)), -1):
        if re.search(r"(^|— )(the end|fin|fine|ende|finis|slut)[.!]?$", out[i][1].strip(), re.I):
            out = out[:i + 1]
            break
    # 6) seuls les vrais titres de chapitre (Chapitre, Livre, Acte…) ouvrent une page et vont au sommaire ;
    #    les autres titres (lettres, sous-titres, légendes) deviennent des intertitres « s »
    strict = re.compile(r"^(?i:chapter|chapitre|kapitel|capitolo|capítulo|cap[ií]tulo|book|livre|buch|libro|part|partie|teil|parte|"
                        r"volume|tome|act|acte|aufzug|atto|jornada|canto|chant|gesang|stave|canzone|giornata|novella)\b"
                        r"|^[IVXLC]+[.:](\s|$)|^[IVXLC]+$|^\d{1,3}[.:]?(\s|$)")
    for rx in (strict, head_re):
        main = sum(1 for k, t in out if k == "h" and rx.search(t))
        if main >= 5:
            out = [("s" if k == "h" and not rx.search(t) else k, t) for k, t in out]
            break
    # titres sans aucun texte après eux (restes de navigation « Chapitre I — Chapitre II » en fin de livre)
    bare = re.compile(r"^((?i:chapitre|chapter|capitolo|kapitel|capítulo|livre|partie|part|book)\s+)?[IVXLC]+\.?"
                      r"(\s*[—–-]\s*((?i:chapitre|chapter|capitolo|kapitel|capítulo|livre|partie|part|book)\s+)?[IVXLC]+\.?)?$|"
                      r"^(?i:premi[eè]re|deuxi[eè]me|troisi[eè]me)\s+(?i:partie)\.?$")
    part_rx = r"(?i:premi[eè]re|deuxi[eè]me|troisi[eè]me|first|second|third)\s+(?i:partie|part)\.?"
    bare2 = re.compile(r"^(" + part_rx + r")(\s*[—–-]\s*" + part_rx + r")?$")
    nav2 = re.compile(r"^(?i:chapitre|chapter|capitolo|kapitel|capítulo)\s+[IVXLC]+\.?\s*[—–-]\s*(?i:chapitre|chapter|capitolo|kapitel|capítulo)\s+[IVXLC]+\.?$")
    out = [(k, t) for k, t in out if not (k in ("h", "s") and nav2.match(t.strip()))]
    keep, after_is_empty = [], True       # on parcourt depuis la fin
    for i in range(len(out) - 1, -1, -1):
        k, t = out[i]
        if k in ("h", "s") and (bare.match(t.strip()) or bare2.match(t.strip())) and after_is_empty and i > len(out) * 0.5:
            continue
        after_is_empty = k in ("h", "s")
        keep.append((k, t))
    out = keep[::-1]
    # fin de livre : renvois de notes (« C. », « L. », « Book i. chap. 5. ») pris pour des titres
    tail = int(len(out) * 0.92)
    for i in range(tail, len(out)):
        k, t = out[i]
        if k == "h" and (len(t.strip(" .")) <= 2 or re.match(r"^book [ivxl\d]+\.? ch(ap)?\.? ?[ivxl\d]+\.?$", t.strip(), re.I)):
            out[i] = ("p", t)
    hs = [i for i, (k, t) in enumerate(out) if k == "h"]
    if len(hs) >= 40:
        sizes = [sum(len(t.split()) for _, t in out[a + 1:b]) for a, b in zip(hs, hs[1:] + [len(out)])]
        if statistics.median(sizes) < 150:
            out = [("s" if k == "h" else k, t) for k, t in out]
    return out

# ------------------------------------------------------------------ couverture
PALETTES = [("#16302b", "#e9c46a", "#f4ecd8"), ("#2d1e3e", "#e8a87c", "#f6ede4"), ("#3b1f19", "#e9b872", "#f7ecdc"),
            ("#0f2a44", "#8ecae6", "#eef6fb"), ("#2f3e2c", "#d4a373", "#f3efe6"), ("#1d1d1f", "#d9b26f", "#f2ede3"),
            ("#4a1526", "#f2c6a0", "#fbefe6"), ("#1b3a4b", "#f4a261", "#fdf1e6")]

def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines

def cover_svg(title, author, seed, lang="en"):
    if lang in RTL:
        return cover_svg_rtl(title, author, seed)
    bg, accent, paper = PALETTES[seed % len(PALETTES)]
    lines = wrap(title, 14)
    size = 150 if len(lines) <= 2 else 124 if len(lines) <= 3 else 104
    y0 = 1180 - (len(lines) - 1) * size * 0.55
    tl = "".join(f'<text x="160" y="{y0 + i * size * 1.1:.0f}" font-size="{size}" font-weight="600" '
                 f'font-family="Libertinus Serif, Georgia, serif" fill="{paper}">{html.escape(l)}</text>' for i, l in enumerate(lines))
    ay = y0 + len(lines) * size * 1.1 + 70
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2400" viewBox="0 0 1600 2400">
<rect width="1600" height="2400" fill="{bg}"/>
<circle cx="1120" cy="560" r="300" fill="{accent}" opacity=".92"/>
<circle cx="1120" cy="560" r="210" fill="none" stroke="{bg}" stroke-width="12" opacity=".5"/>
<circle cx="1120" cy="560" r="120" fill="{bg}" opacity=".18"/>
<rect x="160" y="930" width="140" height="10" fill="{accent}"/>
{tl}
<text x="160" y="{ay:.0f}" font-size="68" font-style="italic" font-family="Libertinus Serif, Georgia, serif" fill="{accent}">{html.escape(author)}</text>
<text x="160" y="2230" font-size="44" letter-spacing="14" font-family="Libertinus Serif, Georgia, serif" fill="{paper}" opacity=".75">BOOKCLASSICS</text>
</svg>'''

def cover_svg_rtl(title, author, seed):
    bg, accent, paper = PALETTES[seed % len(PALETTES)]
    lines = wrap(title, 12)
    size = 170 if len(lines) <= 2 else 140 if len(lines) <= 3 else 116
    y0 = 1180 - (len(lines) - 1) * size * 0.6
    ff = "Amiri, Noto Naskh Arabic, serif"
    tl = "".join(f'<text x="1440" y="{y0 + i * size * 1.25:.0f}" text-anchor="end" direction="rtl" font-size="{size}" font-weight="700" '
                 f'font-family="{ff}" fill="{paper}">{html.escape(l)}</text>' for i, l in enumerate(lines))
    ay = y0 + len(lines) * size * 1.25 + 60
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2400" viewBox="0 0 1600 2400">
<rect width="1600" height="2400" fill="{bg}"/>
<circle cx="480" cy="560" r="300" fill="{accent}" opacity=".92"/>
<circle cx="480" cy="560" r="210" fill="none" stroke="{bg}" stroke-width="12" opacity=".5"/>
<circle cx="480" cy="560" r="120" fill="{bg}" opacity=".18"/>
<rect x="1300" y="930" width="140" height="10" fill="{accent}"/>
{tl}
<text x="1440" y="{ay:.0f}" text-anchor="end" direction="rtl" font-size="80" font-family="{ff}" fill="{accent}">{html.escape(author)}</text>
<text x="160" y="2230" font-size="44" letter-spacing="14" font-family="Libertinus Serif, Georgia, serif" fill="{paper}" opacity=".75">BOOKCLASSICS</text>
</svg>'''

def have(tool):
    return shutil.which(tool) is not None

def run(cmd, cwd=None):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)

def svg_to_png(svg_path, png_path):
    """Couverture PNG via Typst (déjà installé), sinon rsvg/ImageMagick."""
    if have("typst"):
        d = os.path.dirname(svg_path)
        typ = os.path.join(d, "_cover.typ")
        with open(typ, "w", encoding="utf-8") as f:
            f.write(f'#set page(width: 1600pt, height: 2400pt, margin: 0pt)\n#image("{os.path.basename(svg_path)}", width: 100%, height: 100%)\n')
        r = run(["typst", "compile", "--format", "png", "--ppi", "72", typ, png_path])
        os.remove(typ)
        if r.returncode == 0 and os.path.exists(png_path):
            return True
    for cmd in (["rsvg-convert", "-o", png_path, svg_path], ["magick", svg_path, png_path], ["convert", svg_path, png_path]):
        if have(cmd[0]) and run(cmd).returncode == 0 and os.path.exists(png_path):
            return True
    return False

# ------------------------------------------------------------------ HTML de lecture
CSS = """
:root{--paper:#fbf8f1;--ink:#1f1b16;--muted:#6f6352;--accent:#9a6b2f;--rule:#e4dccb}
@media (prefers-color-scheme:dark){:root{--paper:#16140f;--ink:#ece6d8;--muted:#a79c88;--accent:#d8a95e;--rule:#2e2a22}}
html{background:var(--paper)}
body{font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Libertinus Serif",Georgia,serif;color:var(--ink);
     background:var(--paper);line-height:1.65;font-size:1.12rem;max-width:36em;margin:0 auto;padding:2.5em 1.25em 5em}
.titlepage{text-align:center;min-height:70vh;display:flex;flex-direction:column;justify-content:center;gap:.6em;
           border-bottom:1px solid var(--rule);margin-bottom:2.5em;padding-bottom:2.5em}
.titlepage img{max-width:260px;width:60%;margin:0 auto 1.5em;border-radius:4px;box-shadow:0 10px 30px rgba(0,0,0,.18)}
h1{font-size:2.4em;line-height:1.15;font-weight:600;margin:0;letter-spacing:-.01em}
.author{font-style:italic;font-size:1.25em;color:var(--accent);margin:0}
.translator{font-size:.95em;color:var(--muted);margin:0}
nav.toc{margin:0 0 3em}
nav.toc h2{font-size:.85em;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);text-align:left;margin:0 0 .8em}
nav.toc ol{list-style:none;padding:0;margin:0;columns:1}
nav.toc li{margin:.25em 0}
nav.toc a{color:var(--ink);text-decoration:none;border-bottom:1px solid transparent}
nav.toc a:hover{border-color:var(--accent)}
h2.chapter{font-size:1.45em;font-weight:600;text-align:center;margin:3.5em 0 1.6em;line-height:1.3}
h2.chapter::before{content:"";display:block;width:3em;height:2px;background:var(--accent);margin:0 auto 1.1em}
p{margin:0;text-indent:1.5em;text-align:justify;hyphens:auto;-webkit-hyphens:auto}
h2.chapter + p, .titlepage + p{text-indent:0}
h2.chapter + p::first-letter{font-size:3.1em;float:left;line-height:.85;padding:.08em .08em 0 0;color:var(--accent);font-weight:600}
.colophon{margin-top:5em;padding-top:1.5em;border-top:1px solid var(--rule);text-align:center;color:var(--muted);font-size:.85em;text-indent:0}
h3.sub{font-size:1em;font-weight:600;font-variant:small-caps;letter-spacing:.04em;text-align:center;margin:2.2em 0 1em}
h3.sub + p{text-indent:0}
@media print{h2.chapter{break-before:page}}
"""

def build_html(title, author, lang, blocks, credit, cover_rel=None, toc=True):
    lab = labels(lang)
    tr = translator_line(credit, lang)
    heads = [t for k, t in blocks if k == "h"]
    rtl = lang in RTL
    dir_attr = ' dir="rtl"' if rtl else ''
    extra_css = AR_CSS if rtl else ''
    out = [f'<!DOCTYPE html>\n<html lang="{lang}"{dir_attr}><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f"<title>{html.escape(title)} — {html.escape(author)}</title><style>{CSS}{extra_css}</style></head><body>",
           '<header class="titlepage">']
    if cover_rel:
        out.append(f'<img src="{html.escape(cover_rel)}" alt="">')
    out += [f"<h1>{html.escape(title)}</h1>", f'<p class="author">{html.escape(author)}</p>']
    if tr:
        out.append(f'<p class="translator">{html.escape(tr)}</p>')
    out.append("</header>")
    if toc and len(heads) >= 3:
        out.append(f'<nav class="toc"><h2>{lab[0]}</h2><ol>')
        n = 0
        for k, t in blocks:
            if k == "h":
                n += 1
                out.append(f'<li><a href="#c{n}">{html.escape(t)}</a></li>')
        out.append("</ol></nav>")
    n = 0
    for k, t in blocks:
        if k == "h":
            n += 1
            out.append(f'<h2 class="chapter" id="c{n}">{html.escape(t)}</h2>')
        elif k == "s":
            out.append(f'<h3 class="sub">{html.escape(t)}</h3>')
        else:
            out.append(f"<p>{html.escape(t)}</p>")
    out.append(f'<p class="colophon">{html.escape(lab[4])} {html.escape(lab[3])}.</p>')
    out.append("</body></html>")
    return "\n".join(out)

def build_txt(title, author, lang, blocks, credit):
    lab = labels(lang)
    tr = translator_line(credit, lang)
    head = [title, author] + ([tr] if tr else [])
    body = []
    for k, t in blocks:
        body.append(f"\n\n{t.upper()}\n" if k == "h" else f"\n{t}\n" if k == "s" else t)
    return "\n".join(head) + "\n\n\n" + "\n\n".join(body).strip() + f"\n\n\n— {lab[4]} {lab[3]}.\n"

# ------------------------------------------------------------------ EPUB
EPUB_CSS = """
body{font-family:serif;line-height:1.55;margin:0 5%}
h1{font-size:2em;text-align:center;margin:30% 0 .3em;font-weight:600}
.author{text-align:center;font-style:italic;font-size:1.2em;margin:0}
.translator{text-align:center;font-size:.95em;margin:.6em 0 0;color:#555}
h2.chapter{font-size:1.35em;text-align:center;margin:3em 0 1.4em;font-weight:600;page-break-before:always}
p{margin:0;text-indent:1.4em;text-align:justify;-webkit-hyphens:auto;hyphens:auto}
h2.chapter + p, h3.sub + p{text-indent:0}
h3.sub{font-size:1em;font-weight:600;font-variant:small-caps;text-align:center;margin:2em 0 1em}
.colophon{margin-top:4em;text-align:center;font-size:.85em;color:#666;text-indent:0}
"""

def make_epub(html_path, epub_path, title, author, lang, cover, workdir, credit=""):
    css_path = os.path.join(workdir, "_epub.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(EPUB_CSS + (AR_CSS if lang in RTL else ""))
    base = ["pandoc", html_path, "-f", "html", "-t", "epub3", "-o", epub_path, "--toc", "--toc-depth=1",
            "--css", css_path, "--metadata", f"title={title}", "--metadata", f"author={author}",
            "--metadata", f"lang={lang}", "--metadata", "publisher=BookClassics",
            "--metadata", f"rights={labels(lang)[4]}"] + (["--metadata", "dir=rtl"] if lang in RTL else [])
    tr = translator_line(credit, lang)
    if tr and ("by" in tr or "de " in tr or "von" in tr or "di " in tr or "av " in tr):
        base += ["--metadata", f"contributor={tr}"]
    if cover:
        base += ["--epub-cover-image", cover]
    for extra in (["--split-level=2"], ["--epub-chapter-level=2"], []):
        if run(base + extra).returncode == 0 and os.path.exists(epub_path):
            return True
    return False

# ------------------------------------------------------------------ PDF (Typst)
def tq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

TYPST_HEAD = r'''
#let booktitle = TITLE
#let bookauthor = AUTHOR
#set document(title: booktitle, author: bookauthor)
#set text(font: ("Libertinus Serif", "Linux Libertine", "New Computer Modern"), size: 10.5pt, lang: LANG, hyphenate: true)
#set par(justify: true, leading: 0.68em, first-line-indent: 1.3em, spacing: 0.68em)
#set page(width: 6in, height: 9in, margin: (inside: 0.85in, outside: 0.7in, top: 0.85in, bottom: 0.8in))
#let chap(t) = {
  pagebreak(weak: true)
  v(1.6in)
  align(center, block(width: 85%)[
    #line(length: 2.2em, stroke: 1pt + rgb("#9a6b2f"))
    #v(0.6em)
    #heading(level: 1, outlined: true, bookmarked: true)[#text(size: 15pt, weight: "semibold", t)]
  ])
  v(1.2em)
}
#show heading.where(level: 1): it => it.body
#let sub(t) = { v(1.2em); align(center, text(weight: "semibold", smallcaps(t))); v(0.5em) }
#let p(t) = par(t)
'''

def build_typst(title, author, lang, blocks, credit, cover_name):
    lab = labels(lang)
    tr = translator_line(credit, lang)
    head = TYPST_HEAD
    if lang in RTL:
        head = head.replace('#set text(font: ("Libertinus Serif", "Linux Libertine", "New Computer Modern"), size: 10.5pt, lang: LANG, hyphenate: true)',
                            '#set text(font: ("Amiri", "Noto Naskh Arabic", "Libertinus Serif"), size: 12.5pt, lang: LANG, dir: rtl, hyphenate: false)')
        head = head.replace("first-line-indent: 1.3em, spacing: 0.68em", "first-line-indent: 0em, spacing: 0.9em").replace("leading: 0.68em", "leading: 0.9em")
    parts = [head.replace("TITLE", tq(title)).replace("AUTHOR", tq(author)).replace("LANG", tq(lang))]
    if cover_name:
        parts.append(f'#page(margin: 0pt, header: none, footer: none)[#image({tq(cover_name)}, width: 100%, height: 100%, fit: "cover")]')
    parts.append(f'''#page(header: none, footer: none)[
  #v(1.8in)
  #align(center)[
    #text(size: 24pt, weight: "semibold", {tq(title)})
    #v(1.2em)
    #text(size: 13pt, style: "italic", fill: rgb("#9a6b2f"), {tq(author)})
    {"#v(0.8em) #text(size: 10pt, fill: luma(90), " + tq(tr) + ")" if tr else ""}
  ]
  #v(1fr)
  #align(center, text(size: 8.5pt, fill: luma(110), {tq(lab[4] + " " + lab[3] + ".")}))
]''')
    heads = sum(1 for k, _ in blocks if k == "h")
    if heads >= 3:
        parts.append(f'#page(header: none)[#outline(title: {tq(lab[0])}, indent: 0pt, depth: 1)]')
    # en-têtes courants et numéros de page pour le corps du livre
    parts.append(f'''#set page(
  header: context {{
    let n = counter(page).get().first()
    set text(size: 8pt, fill: luma(110))
    if calc.even(n) {{ align(left, smallcaps(bookauthor)) }} else {{ align(right, emph(booktitle)) }}
  }},
  footer: context align(center, text(size: 8.5pt, fill: luma(110), counter(page).display())),
)
#counter(page).update(1)''')
    first = True
    for k, t in blocks:
        if k == "h":
            parts.append(f"#chap({tq(t)})")
            first = True
        elif k == "s":
            parts.append(f"#sub({tq(t)})")
            first = True
        else:
            if first:
                parts.append(f"#par(first-line-indent: 0pt, {tq(t)})")
                first = False
            else:
                parts.append(f"#p({tq(t)})")
    return "\n".join(parts) + "\n"

def make_pdf(typ_src, pdf_path, workdir, html_path=None):
    if have("typst"):
        typ = os.path.join(workdir, "_book.typ")
        with open(typ, "w", encoding="utf-8") as f:
            f.write(typ_src)
        r = run(["typst", "compile", typ, pdf_path])
        os.remove(typ)
        if r.returncode == 0 and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000:
            return True
        with open(os.path.join(workdir, "_typst_error.txt"), "w", encoding="utf-8") as f:
            f.write(r.stderr[-4000:])
    if html_path and have("weasyprint"):
        if run(["weasyprint", html_path, pdf_path]).returncode == 0:
            return True
    return False
