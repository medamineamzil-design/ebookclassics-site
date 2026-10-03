#!/usr/bin/env python3
"""
EbookClassics — production automatique des livres (lot 30 + lot 2) (SANS IA, 0 crédit API).

Pour chaque livre : télécharge le texte sur Project Gutenberg, le nettoie,
puis fabrique 4 formats (EPUB, PDF, TXT, HTML) + une couverture moderne (SVG/PNG),
avec les noms de fichiers attendus par le site :
    <slug>/<slug>.<ext>        (anglais)
    <slug>/<slug>-fr.<ext>     (français)

Usage :
    python3 ebooks_lot30.py            # produit tout le lot
    python3 ebooks_lot30.py dracula    # seulement les livres dont le slug contient "dracula"

Sortie : ~/ebookclassics-lot30/   (rapport : ~/ebookclassics-lot30/RAPPORT.txt)
Rien n'est envoyé sur GitHub : la publication se fait ensuite, séparément.
"""
import html, json, os, re, shutil, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

OUT = os.path.expanduser("~/ebookclassics-lot30")
UA = {"User-Agent": "EbookClassics-builder/1.0 (personal project)"}

# (titre EXACT du site, auteur, [(langue, id Gutenberg, mots-clés de vérification du titre)])
# id=None -> recherche automatique (gutendex) par titre + langue.
BOOKS = [
    ("Wuthering Heights", "Emily Brontë", [("en", 768, "wuthering")]),
    ("Jane Eyre", "Charlotte Brontë", [("en", 1260, "jane eyre")]),
    ("Dracula", "Bram Stoker", [("en", 345, "dracula")]),
    ("Great Expectations", "Charles Dickens", [("en", 1400, "great expectations")]),
    ("The Picture of Dorian Gray", "Oscar Wilde", [("en", 174, "dorian gray")]),
    ("The Strange Case of Dr Jekyll and Mr Hyde", "Robert Louis Stevenson", [("en", 43, "jekyll")]),
    ("The Adventures of Sherlock Holmes", "Arthur Conan Doyle", [("en", 1661, "sherlock holmes")]),
    ("Alice's Adventures in Wonderland", "Lewis Carroll", [("en", 11, "wonderland")]),
    ("Moby-Dick", "Herman Melville", [("en", 2701, "moby")]),
    ("The Adventures of Huckleberry Finn", "Mark Twain", [("en", 76, "huckleberry")]),
    ("The Adventures of Tom Sawyer", "Mark Twain", [("en", 74, "tom sawyer")]),
    ("The Count of Monte Cristo", "Alexandre Dumas", [("en", 1184, "monte cristo")]),
    ("The Three Musketeers", "Alexandre Dumas", [("en", 1257, "three musketeers"), ("fr", 13951, "trois mousquetaires")]),
    ("Twenty Thousand Leagues Under the Sea", "Jules Verne", [("en", 164, "twenty thousand"), ("fr", 5097, "vingt mille")]),
    ("The Hound of the Baskervilles", "Arthur Conan Doyle", [("en", 2852, "baskervilles")]),
    ("The Time Machine", "H. G. Wells", [("en", 35, "time machine")]),
    ("The War of the Worlds", "H. G. Wells", [("en", 36, "war of the worlds")]),
    ("The Invisible Man", "H. G. Wells", [("en", 5230, "invisible man")]),
    ("The Call of the Wild", "Jack London", [("en", 215, "call of the wild")]),
    ("Little Women", "Louisa May Alcott", [("en", 514, "little women")]),
    ("The Secret Garden", "Frances Hodgson Burnett", [("en", 113, "secret garden")]),
    ("The Wonderful Wizard of Oz", "L. Frank Baum", [("en", 55, "wizard of oz")]),
    ("Peter Pan", "J. M. Barrie", [("en", 16, "peter pan")]),
    ("Anne of Green Gables", "L. M. Montgomery", [("en", 45, "green gables")]),
    ("The Jungle Book", "Rudyard Kipling", [("en", 236, "jungle book")]),
    ("The Wind in the Willows", "Kenneth Grahame", [("en", 289, "willows")]),
    ("Heart of Darkness", "Joseph Conrad", [("en", 219, "heart of darkness")]),
    ("Candide", "Voltaire", [("en", 19942, "candide"), ("fr", 4650, "candide")]),
    ("Madame Bovary", "Gustave Flaubert", [("en", 2413, "bovary"), ("fr", 14155, "bovary")]),
    ("The Phantom of the Opera", "Gaston Leroux", [("en", 175, "phantom"), ("fr", None, "fantome opera")]),
    # ---------------- pilote (refait avec la nouvelle mise en forme) ----------------
    ("Pride and Prejudice", "Jane Austen", [("en", 1342, "pride and prejudice")]),
    ("Frankenstein", "Mary Shelley", [("en", 84, "frankenstein")]),
    ("Les Misérables", "Victor Hugo", [("en", 135, "miserables")]),
    # ---------------- LOT 2 : livres du site pas encore produits ----------------
    ("War and Peace", "Leo Tolstoy", [("en", 2600, "war and peace")]),
    ("Crime and Punishment", "Fyodor Dostoevsky", [("en", 2554, "crime and punishment")]),
    ("Anna Karenina", "Leo Tolstoy", [("en", 1399, "anna karenina")]),
    ("The Great Gatsby", "F. Scott Fitzgerald", [("en", 64317, "gatsby")]),
    ("Don Quixote", "Miguel de Cervantes", [("en", 996, "don quixote"), ("es", 2000, "quijote")]),
    ("The Odyssey", "Homer", [("en", 1727, "odyssey")]),
    ("The Iliad", "Homer", [("en", 6130, "iliad")]),
    ("The Divine Comedy", "Dante Alighieri", [("en", 8800, "divine comedy"), ("it", 1012, "divina commedia")]),
    ("Hamlet", "William Shakespeare", [("en", 1524, "hamlet")]),
    ("Romeo and Juliet", "William Shakespeare", [("en", 1513, "romeo")]),
    ("Faust", "Johann Wolfgang von Goethe", [("en", 14591, "faust"), ("de", 2229, "faust")]),
    ("Meditations", "Marcus Aurelius", [("en", 2680, "meditations")]),
    ("The Prince", "Niccolò Machiavelli", [("en", 1232, "prince"), ("it", None, "principe")]),
    ("The Wealth of Nations", "Adam Smith", [("en", 3300, "wealth of nations")]),
    ("The Theory of Moral Sentiments", "Adam Smith", [("en", 67363, "moral sentiments")]),
    ("Capital, Volume I", "Karl Marx", [("en", None, "capital"), ("de", None, "kapital")]),
    ("The Communist Manifesto", "Karl Marx & Friedrich Engels", [("en", 61, "communist manifesto"), ("de", None, "manifest")]),
    ("On the Principles of Political Economy and Taxation", "David Ricardo", [("en", 33310, "political economy")]),
    ("An Essay on the Principle of Population", "Thomas Malthus", [("en", 4239, "population")]),
    ("Principles of Political Economy", "John Stuart Mill", [("en", 30107, "political economy")]),
    ("The Theory of the Leisure Class", "Thorstein Veblen", [("en", 833, "leisure class")]),
    ("Extraordinary Popular Delusions and the Madness of Crowds", "Charles Mackay", [("en", 24518, "popular delusions")]),
    ("The Federalist Papers", "Alexander Hamilton, James Madison & John Jay", [("en", 1404, "federalist")]),
    ("Aesop's Fables", "Aesop", [("en", 21, "aesop")]),
    ("The Scarlet Letter", "Nathaniel Hawthorne", [("en", 25344, "scarlet letter")]),
    ("Uncle Tom's Cabin", "Harriet Beecher Stowe", [("en", 203, "uncle tom")]),
    ("Common Sense", "Thomas Paine", [("en", 147, "common sense")]),
    ("The Autobiography of Benjamin Franklin", "Benjamin Franklin", [("en", 20203, "autobiography")]),
    ("Second Treatise of Government", "John Locke", [("en", 7370, "government")]),
    ("On Liberty", "John Stuart Mill", [("en", 34901, "liberty")]),
    ("On the Origin of Species", "Charles Darwin", [("en", 1228, "origin of species")]),
    ("The Importance of Being Earnest", "Oscar Wilde", [("en", 844, "earnest")]),
    ("The Last of the Mohicans", "James Fenimore Cooper", [("en", 940, "mohicans")]),
    ("The Island of Doctor Moreau", "H. G. Wells", [("en", 159, "moreau")]),
    ("The Adventures of Pinocchio", "Carlo Collodi", [("en", 500, "pinocchio"), ("it", None, "pinocchio")]),
    ("The Betrothed", "Alessandro Manzoni", [("en", 35155, "betrothed"), ("it", None, "promessi sposi")]),
    ("Heart", "Edmondo De Amicis", [("en", None, "heart"), ("it", None, "cuore")]),
    ("The House by the Medlar Tree", "Giovanni Verga", [("en", None, "medlar"), ("it", None, "malavoglia")]),
    ("The Decameron", "Giovanni Boccaccio", [("en", 23700, "decameron"), ("it", None, "decameron")]),
    ("Metamorphoses", "Ovid", [("en", 21765, "metamorphoses")]),
    ("The Republic", "Plato", [("en", 1497, "republic")]),
    ("Nicomachean Ethics", "Aristotle", [("en", 8438, "ethics")]),
    ("The Descent of Man", "Charles Darwin", [("en", 2300, "descent of man")]),
    ("Walden", "Henry David Thoreau", [("en", 205, "walden")]),
    ("Civil Disobedience", "Henry David Thoreau", [("en", 71, "civil disobedience")]),
    ("The Prince and the Pauper", "Mark Twain", [("en", 1837, "prince and the pauper")]),
    ("The Railway Children", "E. Nesbit", [("en", 1874, "railway children")]),
    ("The Wonderful Adventures of Nils", "Selma Lagerlöf", [("en", None, "nils"), ("sv", None, "nils holgersson")]),
    ("The Pilgrim's Progress", "John Bunyan", [("en", 131, "pilgrim")]),
    ("The Book of Common Prayer", "Church of England", [("en", None, "common prayer")]),
    # ---------------- LOT 5 : classiques très connus ajoutés (26/09/2026) ----------------
    ("Robinson Crusoe", "Daniel Defoe", [("en", 521, "robinson crusoe")]),
    ("Gulliver's Travels", "Jonathan Swift", [("en", 829, "gulliver")]),
    ("Treasure Island", "Robert Louis Stevenson", [("en", 120, "treasure island")]),
    ("Oliver Twist", "Charles Dickens", [("en", 730, "oliver twist")]),
    ("A Tale of Two Cities", "Charles Dickens", [("en", 98, "tale of two cities")]),
    ("A Christmas Carol", "Charles Dickens", [("en", 46, "christmas carol")]),
    ("David Copperfield", "Charles Dickens", [("en", 766, "david copperfield")]),
    ("Emma", "Jane Austen", [("en", 158, "emma")]),
    ("Sense and Sensibility", "Jane Austen", [("en", 161, "sense and sensibility")]),
    ("Persuasion", "Jane Austen", [("en", 105, "persuasion")]),
    ("Tess of the d'Urbervilles", "Thomas Hardy", [("en", 110, "tess")]),
    ("Middlemarch", "George Eliot", [("en", 145, "middlemarch")]),
    ("Vanity Fair", "William Makepeace Thackeray", [("en", 599, "vanity fair")]),
    ("Ulysses", "James Joyce", [("en", 4300, "ulysses")]),
    ("Dubliners", "James Joyce", [("en", 2814, "dubliners")]),
    ("Mrs Dalloway", "Virginia Woolf", [("en", 71865, "dalloway")]),
    ("The Age of Innocence", "Edith Wharton", [("en", 541, "age of innocence")]),
    ("The Scarlet Pimpernel", "Baroness Orczy", [("en", 60, "scarlet pimpernel")]),
    ("Kidnapped", "Robert Louis Stevenson", [("en", 421, "kidnapped")]),
    ("Paradise Lost", "John Milton", [("en", 26, "paradise lost")]),
    ("Beowulf", "Anonymous", [("en", 16328, "beowulf")]),
    ("The Canterbury Tales", "Geoffrey Chaucer", [("en", 2383, "canterbury")]),
    ("Macbeth", "William Shakespeare", [("en", 1533, "macbeth")]),
    ("Othello", "William Shakespeare", [("en", 1531, "othello")]),
    ("King Lear", "William Shakespeare", [("en", 1532, "king lear")]),
    ("A Midsummer Night's Dream", "William Shakespeare", [("en", 1514, "midsummer")]),
    ("The Tempest", "William Shakespeare", [("en", 23042, "tempest")]),
    ("The Brothers Karamazov", "Fyodor Dostoevsky", [("en", 28054, "karamazov")]),
    ("The Idiot", "Fyodor Dostoevsky", [("en", 2638, "idiot")]),
    ("Notes from Underground", "Fyodor Dostoevsky", [("en", 600, "underground")]),
    ("Around the World in Eighty Days", "Jules Verne", [("en", 103, "eighty days"), ("fr", None, "tour du monde")]),
    ("Journey to the Centre of the Earth", "Jules Verne", [("en", 18857, "centre of the earth"), ("fr", None, "voyage au centre")]),
    ("The Hunchback of Notre-Dame", "Victor Hugo", [("en", 2610, "notre dame"), ("fr", None, "notre dame de paris")]),
    ("Germinal", "Émile Zola", [("en", None, "germinal"), ("fr", None, "germinal")]),
    ("The Red and the Black", "Stendhal", [("en", 44747, "red and the black"), ("fr", None, "rouge et le noir")]),
    ("Father Goriot", "Honoré de Balzac", [("en", 1237, "goriot"), ("fr", None, "pere goriot")]),
    ("Bel-Ami", "Guy de Maupassant", [("en", None, "bel ami"), ("fr", None, "bel ami")]),
    ("The Metamorphosis", "Franz Kafka", [("de", 22367, "verwandlung")]),
    ("Grimm's Fairy Tales", "Jacob & Wilhelm Grimm", [("en", 2591, "grimm"), ("de", None, "kinder und hausmarchen")]),
    ("Andersen's Fairy Tales", "Hans Christian Andersen", [("en", 1597, "andersen")]),
    ("The Arabian Nights", "Anonymous", [("en", 128, "arabian nights")]),
    ("The Prophet", "Kahlil Gibran", [("en", 58585, "prophet")]),
    ("Tao Te Ching", "Laozi", [("en", 216, "tao")]),
    ("The Rubaiyat of Omar Khayyam", "Omar Khayyam", [("en", 246, "rubaiyat")]),
]

# ---------------------------------------------------------------- utilitaires
def slug_of(title):
    s = unicodedata.normalize("NFD", title)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60]
    return s.lower()

def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))

def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()

_CATALOG = None
def catalog():
    """Catalogue officiel de Project Gutenberg (CSV, ~15 Mo), telecharge une seule fois."""
    global _CATALOG
    if _CATALOG is None:
        import csv, io
        path = os.path.expanduser("~/.cache/pg_catalog.csv")
        if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 30 * 86400:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            print("  (telechargement du catalogue Gutenberg...)", flush=True)
            data = fetch("https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv")
            open(path, "wb").write(data)
        with open(path, encoding="utf-8", errors="replace") as f:
            _CATALOG = [r for r in csv.DictReader(f) if r.get("Type") == "Text"]
    return _CATALOG

def catalog_find(query, lang, author):
    words = norm(query).split()
    surname = norm(author).replace("&", " ").split(",")[0].split()
    surname = [w for w in surname if len(w) > 2][-1:] or [""]
    hits = []
    for r in catalog():
        if lang not in (r.get("Language") or "").split("; "):
            continue
        t, a = norm(r.get("Title")), norm(r.get("Authors"))
        if all(w in t for w in words) and surname[0] in a:
            if re.search(r"\b(vol(ume)?|tome|band|part|parte|livre)\b\.?\s*[0-9ivx]+\b", t):
                continue  # on evite les volumes separes
            hits.append((len(t), int(r["Text#"])))
    return min(hits)[1] if hits else None

def gutendex_find(query, lang, author=""):
    return catalog_find(query, lang, author)

def get_text(gid):
    for url in (f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
                f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
                f"https://www.gutenberg.org/ebooks/{gid}.txt.utf-8"):
        try:
            raw = fetch(url)
            return raw.decode("utf-8-sig", errors="replace")
        except Exception:
            continue
    raise RuntimeError(f"texte introuvable pour Gutenberg #{gid}")

def header_title(raw):
    m = re.search(r"^Title:\s*(.+)$", raw, re.M)
    return (m.group(1).strip() if m else "")

LANG_NAMES = {"en": "english", "fr": "french", "es": "spanish", "it": "italian", "de": "german", "sv": "swedish",
              "pt": "portuguese", "ru": "russian", "ca": "catalan", "zh": "chinese", "ja": "japanese"}
def header_ok(raw, check, lang):
    t = norm(header_title(raw))
    m = re.search(r"^Language:\s*(.+)$", raw, re.M)
    lang_ok = (not m) or LANG_NAMES.get(lang, lang) in m.group(1).lower()
    return all(w in t for w in norm(check).split()) and lang_ok

def strip_gutenberg(raw):
    s = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\n", raw, re.I)
    e = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK", raw, re.I)
    body = raw[s.end() if s else 0: e.start() if e else len(raw)]
    body = body.replace("\r\n", "\n")
    # retire les mentions de production en tête
    body = re.sub(r"^\s*(Produced by|Transcribed by|E-text prepared by)[^\n]*(\n[^\n]+)*\n", "", body, flags=re.I)
    return body.strip("\n")

HEAD_RE = re.compile(
    r"^(chapter|chapitre|letter|lettre|book|livre|part|partie|volume|tome|stave|adventure|"
    r"preface|préface|introduction|epilogue|épilogue|prologue|conclusion|avant-propos|"
    r"act|acte|scene|scène|canto|chant|capitolo|kapitel|capítulo|essay|fable|"
    r"aufzug|auftritt|szene|akt|buch|teil|libro|parte|atto|jornada|cantar)\b"
    r"|^(?-i:[IVXLC]+)\.?(\s|$)"
    r"|^(?-i:[A-Z]{4,})\s+No\.\s*\d+\.?$"
    r"|^\S+\s+(kapitel|chapitre|capitolo|capítulo|chapter|aufzug|buch|teil|livre|libro|parte|book|part)\b", re.I)

# notes techniques des transcripteurs, illustrations absentes, cadres ASCII : retirés
JUNK_BLOCK = re.compile(
    r"^\[(illustration|ilustraci[oó]n|illustrazione|abbildung|bild|gravure)[^\]]*\]?$"
    r"|transcriber'?s? note|note du transcripteur|nota del transcriptor|anmerkung"
    r"|end of (the )?project gutenberg|ende dieses projekt gutenberg|fin (du|de ce) projet gutenberg|combination of etexts|etexts? (was|were) prepared"
    r"|graciously contributed|projekt-de|produced by|e-text prepared|etext prepared|\.jpg\b|full size|gutcheck|jeebies"
    r"|there are several editions of this ebook|^\+[-=]{5,}|^\|.*\|$", re.I)

def to_blocks(body):
    """Découpe en blocs (paragraphes), retire les notes techniques et repère les titres de chapitres."""
    blocks = []
    for chunk in re.split(r"\n\s*\n", body):
        lines = [l.strip() for l in chunk.split("\n") if l.strip()]
        if not lines:
            continue
        text = " ".join(lines)
        text = re.sub(r"\[(Illustration|Ilustración|Illustrazione|Abbildung)[^\]]*\]", "", text, flags=re.I).strip()
        if not text or JUNK_BLOCK.search(text) and len(text) < 1500:
            continue
        text = re.sub(r"_(.+?)_", r"\1", text)  # italiques Gutenberg _mot_
        is_head = (len(lines) <= 3 and len(text) <= 160 and HEAD_RE.search(text) and not text.rstrip().endswith((",", ";"))) or \
                  (len(lines) == 1 and len(text) <= 60 and text.isupper() and len(text) > 3)
        blocks.append(("h" if is_head else "p", text))
    return blocks

CSS = """
@page { margin: 22mm 20mm; }
body { font-family: Georgia, 'Iowan Old Style', 'Palatino Linotype', serif; line-height: 1.6;
       color: #1f1a14; max-width: 38em; margin: 0 auto; padding: 1.5em 1.2em; }
h1 { font-size: 2.1em; text-align: center; margin: 1.5em 0 .2em; letter-spacing: .01em; }
.author { text-align: center; font-size: 1.15em; font-style: italic; margin-bottom: 3em; color: #5a4a36; }
h2 { font-size: 1.25em; text-align: center; margin: 2.6em 0 1.2em; letter-spacing: .06em;
     text-transform: uppercase; font-weight: normal; page-break-before: always; break-before: page; }
p { margin: 0; text-indent: 1.4em; text-align: justify; hyphens: auto; }
h2 + p, .first { text-indent: 0; }
.colophon { font-size: .85em; color: #6b5d45; text-align: center; margin-top: 4em; text-indent: 0; }
"""

def build_html(title, author, lang, blocks, source_note):
    out = [f'<!DOCTYPE html>\n<html lang="{lang}"><head><meta charset="utf-8">',
           f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>",
           f"<h1>{html.escape(title)}</h1>", f'<p class="author">{html.escape(author)}</p>']
    for kind, text in blocks:
        t = html.escape(text)
        out.append(f"<h2>{t}</h2>" if kind == "h" else f"<p>{t}</p>")
    out.append(f'<p class="colophon">{html.escape(source_note)}</p>')
    out.append("</body></html>")
    return "\n".join(out)

PALETTES = [("#1d3b33", "#e8c872"), ("#2b2140", "#e7b7a3"), ("#3a1f1a", "#f0d9a8"),
            ("#13304a", "#9fd3c7"), ("#40301d", "#f4e1c1"), ("#243b2a", "#f2c14e"),
            ("#4a1c2a", "#f6d6b8"), ("#1c2b45", "#f5b971")]

def build_cover_svg(title, author, seed):
    bg, fg = PALETTES[seed % len(PALETTES)]
    words, lines, cur = title.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 16:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y0 = 1000 - (len(lines) - 1) * 70
    tl = "".join(f'<text x="800" y="{y0 + i*140}" text-anchor="middle" font-size="120" '
                 f'font-family="Georgia, serif" fill="{fg}">{html.escape(l)}</text>' for i, l in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="2400" viewBox="0 0 1600 2400">
<rect width="1600" height="2400" fill="{bg}"/>
<rect x="90" y="90" width="1420" height="2220" fill="none" stroke="{fg}" stroke-width="6" opacity=".8"/>
<rect x="130" y="130" width="1340" height="2140" fill="none" stroke="{fg}" stroke-width="2" opacity=".5"/>
<circle cx="800" cy="560" r="150" fill="none" stroke="{fg}" stroke-width="4" opacity=".7"/>
<circle cx="800" cy="560" r="95" fill="{fg}" opacity=".18"/>
{tl}
<line x1="560" y1="{y0 + len(lines)*140 + 20}" x2="1040" y2="{y0 + len(lines)*140 + 20}" stroke="{fg}" stroke-width="4"/>
<text x="800" y="{y0 + len(lines)*140 + 150}" text-anchor="middle" font-size="70" font-style="italic"
 font-family="Georgia, serif" fill="{fg}">{html.escape(author)}</text>
<text x="800" y="2190" text-anchor="middle" font-size="46" letter-spacing="12" font-family="Georgia, serif"
 fill="{fg}" opacity=".85">BOOKCLASSICS</text>
</svg>'''

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def have(tool):
    return shutil.which(tool) is not None

def svg_to_png(svg_path, png_path):
    for cmd in (["rsvg-convert", "-o", png_path, svg_path],
                ["magick", svg_path, png_path],
                ["convert", svg_path, png_path]):
        if have(cmd[0]) and run(cmd).returncode == 0 and os.path.exists(png_path):
            return True
    return False

def make_pdf(html_path, pdf_path):
    attempts = []
    if have("pandoc") and have("typst"):
        attempts.append(["pandoc", html_path, "-o", pdf_path, "--pdf-engine=typst"])
    if have("weasyprint"):
        attempts.append(["weasyprint", html_path, pdf_path])
    if have("wkhtmltopdf"):
        attempts.append(["wkhtmltopdf", "--quiet", "--enable-local-file-access", html_path, pdf_path])
    if have("pandoc"):
        attempts.append(["pandoc", html_path, "-o", pdf_path])
    for cmd in attempts:
        if run(cmd).returncode == 0 and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000:
            return True
    return False

def make_epub(html_path, epub_path, title, author, lang, cover, css_path):
    base = ["pandoc", html_path, "-f", "html", "-t", "epub3", "-o", epub_path, "--toc",
            "--css", css_path, "--metadata", f"title={title}", "--metadata", f"author={author}",
            "--metadata", f"lang={lang}", "--metadata", "publisher=BookClassics"]
    if cover:
        base += ["--epub-cover-image", cover]
    for extra in (["--split-level=2"], ["--epub-chapter-level=2"], []):
        if run(base + extra).returncode == 0 and os.path.exists(epub_path):
            return True
    return False

# ---------------------------------------------------------------- production
def produce(title, author, lang, gid, check, seed, report, raw_text=None, display_title=None, credit="", source=None):
    slug = slug_of(title)
    folder = os.path.join(OUT, slug)
    os.makedirs(folder, exist_ok=True)
    stem = os.path.join(folder, slug if lang == "en" else f"{slug}-{lang}")
    if all(os.path.exists(f"{stem}.{e}") for e in ("epub", "pdf", "txt", "html")):
        report.append(f"= {slug} [{lang}] déjà fait (ignoré)")
        return
    raw = raw_text
    if raw is None and gid:
        raw = get_text(gid)
        if not header_ok(raw, check, lang):
            raw = None  # mauvais numéro : on cherche
    if raw is None:
        gid = gutendex_find(check, lang, author)
        if not gid:
            report.append(f"! {slug} [{lang}] : introuvable sur Gutenberg — IGNORÉ")
            return
        raw = get_text(gid)
    body = strip_gutenberg(raw)
    blocks = to_blocks(body)
    words = sum(len(t.split()) for _, t in blocks)
    if words < 5000:
        report.append(f"! {slug} [{lang}] : texte trop court ({words} mots, Gutenberg #{gid}) — IGNORÉ")
        return
    src = source or f"Project Gutenberg (#{gid})"   # gardé pour le rapport seulement, jamais dans le livre
    import base64, mise_en_forme as MF
    blocks = MF.tidy(blocks, HEAD_RE, lang)
    words = sum(len(t.split()) for _, t in blocks)
    shown = display_title or title
    if not display_title and lang != "en":           # édition non anglaise : titre dans la langue du livre
        ht = header_title(raw_text or raw).split("\n")[0]
        ht = re.sub(r"(,?\s*\d+\.\s*Band|\s+Tome\s+[IVX]+|\s*\((I|II|III)/[IVX]+\)).*$", "", ht, flags=re.I).strip(" .;:")
        if ht:
            shown = ht[:120]
    # couverture moderne (une par livre, partagée entre les langues)
    cover_svg = f"{stem}-cover.svg"          # une couverture par édition, au titre de la langue
    if not os.path.exists(cover_svg):
        with open(cover_svg, "w", encoding="utf-8") as f:
            f.write(MF.cover_svg(shown, author, seed))
    cover_png = f"{stem}-cover.png"
    if not os.path.exists(cover_png):
        MF.svg_to_png(cover_svg, cover_png)
    cover = cover_png if os.path.exists(cover_png) else None
    svg_uri = "data:image/svg+xml;base64," + base64.b64encode(open(cover_svg, "rb").read()).decode()
    # formats
    with open(f"{stem}.html", "w", encoding="utf-8") as f:
        f.write(MF.build_html(shown, author, lang, blocks, credit, svg_uri))
    with open(f"{stem}.txt", "w", encoding="utf-8") as f:
        f.write(MF.build_txt(shown, author, lang, blocks, credit))
    # l'EPUB part d'un HTML sans image intégrée (pandoc ajoute la couverture PNG)
    epub_src = os.path.join(folder, "_epub_src.html")
    with open(epub_src, "w", encoding="utf-8") as f:
        f.write(MF.build_html(shown, author, lang, blocks, credit, None, toc=False))
    ok_epub = MF.make_epub(epub_src, f"{stem}.epub", shown, author, lang, cover, folder, credit)
    os.remove(epub_src)
    typ = MF.build_typst(shown, author, lang, blocks, credit, os.path.basename(cover) if cover else None)
    ok_pdf = MF.make_pdf(typ, f"{stem}.pdf", folder, f"{stem}.html")
    for junk in ("_epub.css",):
        if os.path.exists(os.path.join(folder, junk)):
            os.remove(os.path.join(folder, junk))
    sizes = " ".join(f"{e}:{os.path.getsize(f'{stem}.{e}')//1024}Ko" for e in ("epub", "pdf", "txt", "html")
                     if os.path.exists(f"{stem}.{e}"))
    status = "OK" if ok_epub and ok_pdf else "PARTIEL"
    report.append(f"{'+' if status == 'OK' else '~'} {slug} [{lang}] {status} — {src}, "
                  f"{words} mots, {sum(1 for k,_ in blocks if k=='h')} chapitres — {sizes}")

def main():
    os.makedirs(OUT, exist_ok=True)
    filt = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    report = [f"Lot EbookClassics — {time.strftime('%Y-%m-%d %H:%M')}"]
    for i, (title, author, eds) in enumerate(BOOKS):
        if filt and filt not in slug_of(title):
            continue
        for lang, gid, check in eds:
            print(f"… {title} [{lang}]", flush=True)
            try:
                produce(title, author, lang, gid, check, i, report)
            except Exception as e:
                report.append(f"! {slug_of(title)} [{lang}] ERREUR : {e}")
            print("  " + report[-1], flush=True)
            time.sleep(1)  # politesse envers Gutenberg
    total = 0
    for root, _, files in os.walk(OUT):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    report.append(f"Taille totale : {total/1024/1024:.1f} Mo — dossier : {OUT}")
    with open(os.path.join(OUT, "RAPPORT.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))

if __name__ == "__main__":
    main()
