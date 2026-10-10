#!/usr/bin/env python3
"""Pages indexables BookClassics : /books/, /books/<slug>/, /covers/<slug>.jpg, sitemap.xml, robots.txt.
Usage : python3 build_books.py <index.html du site> <depot livres> <dossier de sortie>"""
import base64, datetime, html, io, json, os, re, sys
from PIL import Image

SITE_INDEX, REPO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://bookclassics.org"
TODAY = datetime.date.today().isoformat()
MAIL = "contact@bookclassics.org"

data = json.load(open(os.path.join(HERE, "books.json")))
BOOKS, BIOS = data["books"], data["bios"]
CAT_LABEL = {c["slug"]: c["label"] for c in data["cats"]}
MAN = json.load(open(os.path.join(REPO, "manifest.json")))["books"]
AUDIO = json.load(open(os.path.join(REPO, "audio.json")))
LANG = {"en": "English", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian", "pt": "Portuguese", "sv": "Swedish", "ar": "Arabic"}
LANG_NATIVE = {"en": "English", "fr": "Français", "de": "Deutsch", "es": "Español", "it": "Italiano", "pt": "Português", "sv": "Svenska", "ar": "العربية"}
ORDER = ["en", "fr", "es", "de", "it", "pt", "sv", "ar"]

site = open(SITE_INDEX, encoding="utf-8").read()
emb = dict(re.findall(r"title:\"([^\"]*)\"", "")) or {}
i = site.index("const BOOKS = ["); j = site.index("\n];", i)
for bid, b64, title in re.findall(r"\{id:'(b\d+)', coverImg:\"data:image/\w+;base64,([^\"]*)\"[^}]*?title:\"([^\"]*)\"", site[i:j]):
    emb[title] = b64
sg_i = site.index("STUDY_GUIDES = ")
GUIDES = json.loads(site[sg_i + 15: site.index("\n", sg_i)].rstrip().rstrip(";"))
sys.path.insert(0, HERE)
import jslit
try:
    PROMO = jslit.const(site, "PROMO_VIDEOS")          # bandes-annonces officielles (par id de livre)
except Exception:
    PROMO = {}
try:
    TRAILERS = json.load(open(os.path.join(HERE, "content", "trailers.json"), encoding="utf-8"))  # ajouts (par slug)
except FileNotFoundError:
    TRAILERS = {}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

def trailer_html(b):
    v = TRAILERS.get(b["slug"]) or PROMO.get(b["id"])
    if not v or not YT_ID.match(v.get("yt", "")):
        return ""
    yid, src = v["yt"], v.get("src", "")
    return (f'<section class="card trailer"><h2>On screen{": " + esc(src) if src else ""}</h2>'
            f'<button type="button" class="yt" data-yt="{yid}" aria-label="Play the trailer{(" of " + esc(src)) if src else ""}">'
            f'<img src="https://i.ytimg.com/vi/{yid}/hqdefault.jpg" alt="" loading="lazy" width="480" height="360">'
            f'<span class="yt-play" aria-hidden="true"></span></button>'
            f'<p class="free" style="margin-top:10px">Trailer of a film or TV adaptation, played from YouTube.</p></section>'
            '<script>document.querySelectorAll(".yt").forEach(function(b){b.addEventListener("click",function(){'
            'var f=document.createElement("iframe");f.src="https://www.youtube-nocookie.com/embed/"+b.dataset.yt+"?autoplay=1&rel=0";'
            'f.title=b.getAttribute("aria-label");f.allow="autoplay; encrypted-media; picture-in-picture; fullscreen";f.allowFullscreen=true;'
            'f.className="yt-frame";b.replaceWith(f);});});</script>')


books = [b for b in BOOKS if b["slug"] in MAN]
esc = html.escape
os.makedirs(os.path.join(OUT, "covers"), exist_ok=True)

def make_cover(b):
    """Couverture 400x600 : fichier du dépôt si présent, sinon couverture intégrée au site."""
    dst = os.path.join(OUT, "covers", b["slug"] + ".jpg")
    src = os.path.join(REPO, b["slug"], b["slug"] + ".jpg")
    try:
        if os.path.exists(src):
            im = Image.open(src)
        elif b["title"] in emb:
            im = Image.open(io.BytesIO(base64.b64decode(emb[b["title"]])))
        else:
            return None
        im = im.convert("RGB")
        im.thumbnail((400, 600), Image.LANCZOS)
        im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
        return im.size
    except Exception as e:
        print("couverture impossible", b["slug"], e)
        return None

def head_of(slug, lang):
    stem = slug if lang == "en" else f"{slug}-{lang}"
    p = os.path.join(REPO, slug, stem + ".txt")
    try:
        return open(p, encoding="utf-8").read(60000)
    except Exception:
        return ""

def local_title(slug, lang):
    t = head_of(slug, lang).split("\n", 1)[0].strip()
    return t[:120]

HEAD_RE = re.compile(r"^\s*(CHAPTER|Chapter|STAVE|Stave|LETTER|Letter|BOOK ONE|BOOK I|Book I|PART ONE|PART I|Part I|ACT I|Act I|FIRST BOOK|I\.|I)\b[^\n]{0,80}$", re.M)

NO_OPENING = {"candide", "the-canterbury-tales", "the-tempest", "grimm-s-fairy-tales", "king-lear", "macbeth",
    "the-importance-of-being-earnest", "beowulf", "faust", "the-odyssey", "the-iliad", "don-quixote", "meditations",
    "nicomachean-ethics", "the-republic", "the-descent-of-man", "the-rubaiyat-of-omar-khayyam", "the-house-by-the-medlar-tree",
    "extraordinary-popular-delusions-and-the-madness-of-crowds", "on-the-origin-of-species", "principles-of-political-economy",
    "persuasion", "the-prophet", "the-metamorphosis"}

import sys as _sys
_sys.path.insert(0, os.path.join(HERE, "content"))
from markers import MARKERS
try:
    MARKERS.update(json.load(open(os.path.join(HERE, "content", "markers_auto.json"), encoding="utf-8")))
except FileNotFoundError:
    pass
try:
    NO_OPENING |= set(json.load(open(os.path.join(HERE, "content", "no_opening.json"))))
except FileNotFoundError:
    pass
ABOUT = json.load(open(os.path.join(HERE, "content", "about_all.json"), encoding="utf-8"))
AUTH_LONG = json.load(open(os.path.join(HERE, "content", "authors_all.json"), encoding="utf-8"))

def full_text(slug):
    for stem in (slug, ) + tuple(f"{slug}-{l}" for l in MAN[slug]):
        p = os.path.join(REPO, slug, stem + ".txt")
        if os.path.exists(p):
            return open(p, encoding="utf-8").read(400000)
    return ""

def opening(slug):
    """Début du livre (domaine public) : ~2 paragraphes visibles + la suite (jusqu'à ~2600 caractères)."""
    if slug in MARKERS:
        txt = full_text(slug)
        i = txt.find(MARKERS[slug])
        if i < 0:
            return []
        body = txt[txt.rfind("\n", 0, i) + 1:]
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
        first = 0
    else:
        if slug in NO_OPENING or not slug.startswith(tuple("abcdefghijklmnopqrstuvwxyz")):
            return []
        txt = head_of(slug, "en") or head_of(slug, next(iter(MAN[slug])))
        body = txt.split("\n", 2)[2] if txt.count("\n") > 2 else txt
        m = HEAD_RE.search(body)
        if m and m.start() < 45000:
            body = body[m.end():]
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
        def ok(p):
            digits = sum(c.isdigit() for c in p)
            return (len(p) > 220 and digits < len(p) * 0.03 and p.count(".") >= 2
                    and not re.match(r"^(contents|table|chapter|preface|introduction)\b", p, re.I)
                    and "gutenberg" not in p.lower())
        first = next((k for k, p in enumerate(paras) if ok(p)), None)
        if first is None:
            return []
    out, n = [], 0
    for p in paras[first:first + 12]:
        if not p:
            continue
        if re.match(r"^(CHAPTER|Chapter|BOOK|Book|PART|Part|LETTER)\b", p) and out:
            break
        out.append(p[:1500] + ("…" if len(p) > 1500 else "")); n += len(p)
        if n > 2600:
            break
    return out

def readmore(paras, visible):
    """Premiers paragraphes visibles ; la suite dans un bloc replié avec un bouton Read more."""
    if len(paras) <= visible:
        return "".join(paras)
    return ("".join(paras[:visible]) + '<div class="rm-more" hidden>' + "".join(paras[visible:]) + '</div>'
            + '<button type="button" class="rm-btn" aria-expanded="false">Read more</button>')

def fmt_duration(sec):
    h, m = divmod(round(sec / 60), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"

CSS = """
:root{--bg:#EAE7DE;--surface:#FFFFFF;--text:#2A2015;--muted:#6B5D45;--border:#D9D4C4;--accent:#A9823D;--accent-ink:#221806;--wood:#20392C;}
@media (prefers-color-scheme: dark){:root{--bg:#151109;--surface:#1E1810;--text:#EEE4CC;--muted:#B3A282;--border:#3A2C18;--accent:#D3AC5C;--accent-ink:#201704;--wood:#13251C;}}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 "Archivo",system-ui,sans-serif;}
a{color:var(--accent);}
.wrap{max-width:1040px;margin:0 auto;padding-inline:16px;}
header.top{background:var(--wood);color:#F6F1E1;}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-block:14px;flex-wrap:wrap;}
header.top a.brand{font:600 1.35rem "Fraunces",serif;color:#F6F1E1;text-decoration:none;}
header.top nav a{color:#E9DDBF;text-decoration:none;margin-left:18px;font-size:.92rem;}
.crumbs{font-size:.85rem;color:var(--muted);padding-block:18px 4px;}
.crumbs a{color:var(--muted);}
h1,h2,h3{font-family:"Fraunces",serif;font-weight:600;line-height:1.2;}
.hero{display:grid;grid-template-columns:240px 1fr;gap:34px;align-items:start;padding-block:18px 10px;}
.cover{width:240px;height:auto;aspect-ratio:2/3;border-radius:6px;box-shadow:0 2px 4px rgba(0,0,0,.12),0 14px 30px rgba(30,20,5,.22);object-fit:cover;background:var(--wood);}
.cover.text{display:flex;flex-direction:column;justify-content:flex-end;padding:22px;color:#F6F1E1;font:600 1.3rem/1.2 "Fraunces",serif;}
.cover.text small{font:400 .85rem "Archivo",sans-serif;opacity:.8;margin-top:8px;}
h1{font-size:clamp(1.9rem,4vw,2.8rem);margin:0 0 4px;}
.by{font-size:1.1rem;margin:0 0 6px;}
.facts{color:var(--muted);font-size:.92rem;margin:0 0 16px;}
.lead{font-size:1.08rem;max-width:62ch;}
.actions{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 8px;}
.btn{display:inline-block;padding:11px 20px;border-radius:999px;text-decoration:none;font-weight:600;font-size:.95rem;border:1px solid var(--accent);}
.btn.primary{background:var(--accent);color:var(--accent-ink);}
.btn.ghost{color:var(--text);}
.free{font-size:.85rem;color:var(--muted);}
section.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 26px;margin:22px 0;}
section.card h2{font-size:1.3rem;margin:0 0 10px;}
.eds{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;}
.eds li{border:1px solid var(--border);border-radius:10px;padding:10px 14px;}
.eds b{display:block;font-family:"Fraunces",serif;font-weight:600;}
.eds span{font-size:.85rem;color:var(--muted);}
blockquote{margin:0;padding-left:18px;border-left:3px solid var(--accent);font-family:"Fraunces",serif;font-size:1.05rem;}
blockquote p{margin:0 0 12px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:18px;}
.grid a{text-decoration:none;color:var(--text);font-size:.88rem;line-height:1.35;}
.grid img,.grid .ph{width:100%;height:auto;aspect-ratio:2/3;object-fit:cover;border-radius:5px;display:block;margin-bottom:7px;background:var(--wood);box-shadow:0 6px 14px rgba(30,20,5,.15);}
.grid .ph{display:flex;align-items:flex-end;padding:10px;color:#F6F1E1;font:600 .9rem "Fraunces",serif;}
.grid small{color:var(--muted);display:block;}
footer.bottom{border-top:1px solid var(--border);padding-block:22px;margin-top:30px;color:var(--muted);font-size:.85rem;}
footer.bottom a{color:var(--muted);margin-right:16px;}
button.btn{font:600 .95rem "Archivo",sans-serif;cursor:pointer;background:transparent;color:var(--text);}
button.btn.primary,a.btn.primary{background:var(--accent);color:var(--accent-ink);}
.btn:hover{box-shadow:0 2px 8px rgba(30,20,5,.12);}
.btn[hidden]{display:none;}
.eds .ed{width:100%;text-align:left;border:1px solid var(--border);border-radius:10px;padding:10px 14px;background:transparent;color:var(--text);cursor:pointer;font:inherit;}
.eds .ed.active{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);}
.eds li{border:0;padding:0;}
.fmts{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:2px 0 12px;font-size:.88rem;color:var(--muted);}
.fmts[hidden],.player[hidden]{display:none;}
.chip{font:600 .85rem "Archivo",sans-serif;padding:7px 14px;border-radius:999px;border:1px solid var(--border);background:var(--surface);color:var(--text);cursor:pointer;}
.chip:hover{border-color:var(--accent);}
.player{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;margin:4px 0 12px;max-width:560px;}
.player audio{width:100%;display:block;}
.player span{display:block;font-size:.8rem;color:var(--muted);margin-top:6px;}
.gate{position:fixed;inset:0;background:rgba(20,15,5,.55);display:flex;align-items:center;justify-content:center;padding:16px;z-index:50;}
.gate[hidden]{display:none;}
.gate-box{position:relative;background:var(--surface);color:var(--text);border-radius:16px;max-width:430px;width:100%;padding:26px 24px;box-shadow:0 20px 60px rgba(0,0,0,.35);}
.gate-box h2{margin:0 0 8px;font-size:1.4rem;}
.gate-box ul{padding-left:20px;margin:10px 0 16px;font-size:.92rem;}
.gate-box label{display:block;font-size:.85rem;font-weight:600;margin-bottom:6px;}
.gate-box input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--border);font:inherit;background:var(--bg);color:var(--text);margin-bottom:12px;}
.gate-box .btn{width:100%;}
.gate-x{position:absolute;top:12px;right:12px;border:0;background:transparent;font-size:1.1rem;cursor:pointer;color:var(--muted);}
.gate-err{color:#8C4030;font-size:.85rem;margin:-6px 0 10px;}
.gate-err[hidden]{display:none;}
.rm-btn{display:inline-block;margin-top:4px;padding:0;border:0;background:none;color:var(--accent);font:600 .9rem "Archivo",sans-serif;cursor:pointer;text-decoration:underline;text-underline-offset:3px;}
.rm-more[hidden]{display:none;}
blockquote .rm-btn{font-family:"Archivo",sans-serif;}
.gate-fine{font-size:.78rem;color:var(--muted);margin:12px 0 0;}
@media (max-width:680px){.hero{grid-template-columns:1fr;gap:20px;}.cover{width:180px;}}

/* ---- Thème Kiosque + Écoute ---- */
:root{--bg:#F6F3EC;--surface:#FFFFFF;--text:#16130F;--muted:#6B655B;--border:#E6E0D3;--accent:#2D4BE0;--accent-ink:#FFFFFF;--wood:#12352A;--lime:#C8F27A;}
@media (prefers-color-scheme: dark){:root{--bg:#F6F3EC;--surface:#FFFFFF;--text:#16130F;--muted:#6B655B;--border:#E6E0D3;--accent:#2D4BE0;--accent-ink:#FFFFFF;--wood:#12352A;}}
body{font-family:"Bricolage Grotesque",system-ui,sans-serif;}
h1,h2,h3,.eds b,blockquote,.cover.text,.grid .ph{font-family:"Bricolage Grotesque",sans-serif;}
h1{font-weight:800;letter-spacing:-.035em;line-height:1;}
h2,h3{font-weight:800;letter-spacing:-.02em;}
header.top{background:#fff;color:var(--text);border-bottom:1px solid var(--border);}
header.top a.brand{font:800 1.5rem "Bricolage Grotesque",sans-serif;letter-spacing:-.03em;color:var(--text);display:flex;align-items:center;gap:10px;}
header.top a.brand::before{content:"";width:30px;height:30px;border-radius:9px;background:var(--accent);display:inline-block;}
header.top nav a{color:var(--text);font-weight:700;padding:8px 12px;border-radius:999px;margin-left:4px;}
header.top nav a:hover{background:var(--bg);}
.wrap{max-width:1120px;}
.cover{border-radius:16px;box-shadow:0 18px 40px rgba(22,19,15,.18);}
.btn{border-radius:999px;font-weight:800;padding:13px 22px;border:1px solid var(--text);}
.btn.primary,button.btn.primary,a.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;}
#bcListen{background:var(--wood);border-color:var(--wood);color:var(--lime);}
button.btn,.chip,.rm-btn,blockquote .rm-btn{font-family:"Bricolage Grotesque",sans-serif;}
section.card{border:0;border-radius:24px;padding:26px 28px;}
.eds .ed{border-radius:14px;background:var(--bg);border:1px solid transparent;}
.eds .ed.active{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);background:#fff;}
blockquote{border-left:4px solid var(--accent);font-family:"Libre Caslon Text",Georgia,serif;font-size:1.05rem;line-height:1.75;}
.player{background:var(--wood);border:0;border-radius:20px;color:#F3EFE4;}
.player span{color:#BFD0C6;}
.grid a{background:#fff;border-radius:18px;padding:10px;}
.grid img,.grid .ph{border-radius:12px;box-shadow:none;}
.rm-btn,a{color:var(--accent);}
.crumbs a{color:var(--muted);}
footer.bottom{background:#fff;}
.gate-box{border-radius:24px;}
"""

def shell(title, desc, path, body, jsonld=None, image=None):
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>\n' if jsonld else ""
    og_img = f'<meta property="og:image" content="{BASE}{image}">\n' if image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta property="og:type" content="book">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{BASE}{path}">
{og_img}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=Libre+Caslon+Display&family=Libre+Caslon+Text:ital@0;1&display=swap">
<style>{CSS}</style>
<meta name="google-adsense-account" content="ca-pub-2867294004113078">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2867294004113078" crossorigin="anonymous"></script>
{ld}</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="/">BookClassics</a>
  <nav><a href="/">Library</a><a href="/books/">All books</a><a href="/about.html">About</a><a href="/contact.html">Contact</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="bottom"><div class="wrap">
  <a href="/">BookClassics</a><a href="/books/">All books</a><a href="/about.html">About</a><a href="/privacy.html">Privacy</a><a href="/contact.html">Contact</a>
  <p>Free public-domain classics to read online, download or listen to.</p>
</div></footer>
<script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "10da7071de6740f782569ee9862d025c"}}'></script>
</body>
</html>
"""

GATE_HTML = """
<div class="gate" id="bcGate" hidden role="dialog" aria-modal="true" aria-labelledby="bcGateTitle">
  <div class="gate-box">
    <button type="button" class="gate-x" id="bcGateClose" aria-label="Close">✕</button>
    <h2 id="bcGateTitle">Free sign-up</h2>
    <p>Enter your email once to read, download and listen to all our books for free.</p>
    <ul><li>Over 120 classics in 7 languages, free</li><li>EPUB, PDF, TXT, HTML and audiobooks</li><li>An email each time new books arrive</li></ul>
    <form id="bcGateForm" novalidate>
      <label for="bcGateEmail">Your email</label>
      <input id="bcGateEmail" type="email" autocomplete="email" placeholder="name@email.com" required>
      <p class="gate-err" id="bcGateErr" hidden>Please enter a valid email address.</p>
      <button class="btn primary" type="submit" id="bcGateBtn">Continue for free</button>
    </form>
    <p class="gate-fine">By continuing, you agree to receive our new-book announcements by email. Unsubscribe in one click from any email. Your address is never shared or sold. <a href="/privacy.html">Privacy</a></p>
  </div>
</div>"""

BOOK_JS = r"""
(function(){
[].forEach.call(document.querySelectorAll('.rm-btn'),function(b){ b.onclick=function(){ var m=b.previousElementSibling; var open=m.hidden; m.hidden=!open; b.textContent=open?'Show less':'Read more'; b.setAttribute('aria-expanded',String(open)); if(!open) b.parentNode.scrollIntoView({block:'nearest'}); }; });
})();
(function(){
var KIT='9985086', REG='ebc_reader_email_v1', RAW='https://raw.githubusercontent.com/medamineamzil-design/ebookclassics-files/main/';
var lang=BC.lang, pending=null, $=function(i){return document.getElementById(i);};
function reg(){try{return !!localStorage.getItem(REG);}catch(e){return false;}}
function gate(fn){ if(reg()){fn();return;} pending=fn; $('bcGateErr').hidden=true; $('bcGate').hidden=false; setTimeout(function(){$('bcGateEmail').focus();},50); }
function closeGate(){ $('bcGate').hidden=true; pending=null; }
$('bcGateClose').onclick=closeGate;
$('bcGate').addEventListener('click',function(e){ if(e.target===$('bcGate')) closeGate(); });
document.addEventListener('keydown',function(e){ if(e.key==='Escape' && !$('bcGate').hidden) closeGate(); });
$('bcGateForm').onsubmit=function(ev){
  ev.preventDefault();
  var em=String($('bcGateEmail').value||'').trim().toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)){ $('bcGateErr').hidden=false; $('bcGateEmail').focus(); return; }
  $('bcGateBtn').disabled=true;
  var ui='EN'; try{ ui=localStorage.getItem('ebc_ui_lang')||'EN'; }catch(e){}
  var fd=new FormData(); fd.append('email_address',em); fd.append('fields[langue]',ui);
  var done=function(){ try{localStorage.setItem(REG,em);}catch(e){} $('bcGateBtn').disabled=false; var n=pending; pending=null; $('bcGate').hidden=true; if(n) n(); };
  fetch('https://app.kit.com/forms/'+KIT+'/subscriptions',{method:'POST',body:fd,mode:'no-cors'}).then(done,done);
};
function fileUrl(ext){ return RAW+BC.slug+'/'+(lang==='en'?BC.slug:BC.slug+'-'+lang)+'.'+ext; }
function save(blob,name){ var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; document.body.appendChild(a); a.click(); setTimeout(function(){URL.revokeObjectURL(a.href); a.remove();},4000); }
function download(ext){
  gate(function(){
    if(ext==='mp3'){ var au=BC.audio[lang]; if(au) window.open(au.u,'_blank','noopener'); return; }
    var chip=document.querySelector('[data-ext="'+ext+'"]'); if(chip){ chip.disabled=true; chip.textContent='…'; }
    fetch(fileUrl(ext)).then(function(r){ if(!r.ok) throw r.status; return r.blob(); })
      .then(function(b){ save(b, BC.slug+'-'+lang+'.'+ext); })
      .catch(function(){ window.open(fileUrl(ext),'_blank','noopener'); })
      .then(function(){ if(chip){ chip.disabled=false; chip.textContent=ext.toUpperCase(); } });
  });
}
function renderFormats(){
  var O=['epub','pdf','txt','html']; var exts=(BC.ed[lang]||[]).slice().sort(function(x,y){return O.indexOf(x)-O.indexOf(y);}); if(BC.audio[lang]) exts.push('mp3');
  $('bcFormats').innerHTML='<span>Choose a format:</span>'+exts.map(function(x){return '<button type="button" class="chip" data-ext="'+x+'">'+x.toUpperCase()+'</button>';}).join('');
  [].forEach.call($('bcFormats').querySelectorAll('.chip'),function(c){ c.onclick=function(){ download(c.dataset.ext); }; });
}
$('bcDl').onclick=function(){ var f=$('bcFormats'); f.hidden=!f.hidden; this.setAttribute('aria-expanded',String(!f.hidden)); if(!f.hidden) renderFormats(); };
var lb=$('bcListen');
if(lb) lb.onclick=function(){ gate(function(){ var au=BC.audio[lang]; if(!au) return; var p=$('bcPlayer');
  var h=Math.floor(au.d/3600), m=Math.round((au.d%3600)/60);
  p.innerHTML='<audio controls autoplay preload="none" src="'+au.u+'"></audio><span>'+(h?h+' h '+(m<10?'0':'')+m+' min':m+' min')+' · LibriVox volunteer recording · public domain</span>';
  p.hidden=false; }); };
function setLang(l){
  lang=l;
  [].forEach.call(document.querySelectorAll('.ed'),function(e){ var on=e.dataset.lang===l; e.classList.toggle('active',on); e.setAttribute('aria-pressed',String(on)); });
  var href='/#lire-'+BC.slug+'.'+l; $('bcRead').href=href; [].forEach.call(document.querySelectorAll('.bcReadLink'),function(a){a.href=href;});
  if(lb) lb.hidden=!BC.audio[l];
  var p=$('bcPlayer'); p.hidden=true; p.innerHTML='';
  if(!$('bcFormats').hidden) renderFormats();
}
[].forEach.call(document.querySelectorAll('.ed'),function(e){ e.onclick=function(){ setLang(e.dataset.lang); }; });
})();
"""

ORIGINS = {
    "beowulf": "Old English epic poem by an unknown poet, composed some time between the 8th and early 11th centuries and preserved in a single manuscript, the Nowell Codex, now in the British Library.",
    "the-arabian-nights": "Collection of Middle Eastern folk tales gathered in Arabic over many centuries, framed by the story of Scheherazade, who tells a new tale each night to postpone her execution.",
}

covers = {b["slug"]: make_cover(b) for b in books}

def cover_tag(b, cls="cover"):
    if covers.get(b["slug"]):
        w, h = covers[b["slug"]]
        return f'<img class="{cls}" src="/covers/{b["slug"]}.jpg" width="{w}" height="{h}" alt="Cover of {esc(b["title"])} by {esc(b["author"])}">'
    return f'<div class="{cls} text">{esc(b["title"])}<small>{esc(b["author"])}</small></div>'

def mini(b):
    img = (f'<img src="/covers/{b["slug"]}.jpg" alt="" loading="lazy">' if covers.get(b["slug"])
           else f'<span class="ph">{esc(b["title"])}</span>')
    return f'<a href="/books/{b["slug"]}/">{img}{esc(b["title"])}<small>{esc(b["author"])}</small></a>'

def year_of(b):
    m = re.search(r"(\d{3,4})\s*$", b.get("meta", "")) or re.search(r"(\d{4})", b.get("meta", ""))
    return m.group(1) if m else ""

urls = [("/", "1.0"), ("/books/", "0.9"), ("/about.html", "0.3"), ("/privacy.html", "0.2"), ("/contact.html", "0.3")]

for b in books:
    s = b["slug"]
    langs = [l for l in ORDER if l in MAN[s]]
    fmts = sorted({f.upper() for l in langs for f in MAN[s][l]}, key=["EPUB", "PDF", "TXT", "HTML"].index)
    audio = AUDIO.get(s, {})
    cat = CAT_LABEL.get(b["cat"], "Classics")
    lang_names = [LANG[l] for l in langs]
    lang_txt = lang_names[0] if len(lang_names) == 1 else ", ".join(lang_names[:-1]) + " and " + lang_names[-1]
    read = f"/#lire-{s}.{langs[0]}"

    eds = []
    for l in langs:
        t = local_title(s, l) or b["title"]
        extra = ", ".join(f.upper() for f in MAN[s][l])
        if l in audio:
            extra += " · audiobook " + fmt_duration(audio[l].get("duration", 0))
        eds.append(f'<li><button type="button" class="ed{" active" if l == langs[0] else ""}" data-lang="{l}" aria-pressed="{str(l == langs[0]).lower()}"><b lang="{l}">{esc(t)}</b><span>{LANG_NATIVE[l]} · {esc(extra)}</span></button></li>')

    about = [f'<p>{esc(x)}</p>' for x in ABOUT.get(s, [])]
    if b.get("note"): about.append(f'<p>{esc(b["note"])}</p>')
    if b["id"] in GUIDES and GUIDES[b["id"]].get("summary"):
        about.append(f'<p>{esc(GUIDES[b["id"]]["summary"])}</p>')
    auth_paras = AUTH_LONG.get(b["author"]) or ([BIOS.get(b["author"])] if BIOS.get(b["author"]) else [])

    bio = BIOS.get(b["author"], "")
    op = opening(s)
    same_author = [x for x in books if x["author"] == b["author"] and x["slug"] != s]
    same_cat = [x for x in books if x["cat"] == b["cat"] and x["slug"] != s and x not in same_author]
    k = BOOKS.index(b)
    same_cat = sorted(same_cat, key=lambda x: (BOOKS.index(x) - k) % len(BOOKS))
    related = (same_author + same_cat)[:6]

    audio_btn = (f'<button type="button" class="btn ghost" id="bcListen"{"" if langs[0] in audio else " hidden"}>Listen to the audiobook</button>') if audio else ""
    facts = " · ".join(x for x in [b.get("meta", ""), cat, f'{b["pages"]} pages' if b.get("pages") else ""] if x)
    title_tag = f'{b["title"]} by {b["author"]} — read online free, EPUB & PDF | BookClassics'
    desc = (f'Read {b["title"]} by {b["author"]} for free: online, or download in {", ".join(fmts)}'
            f'{" — with the audiobook" if audio else ""}. Editions in {lang_txt}. {b["desc"]}')[:300]

    body = f"""<p class="crumbs"><a href="/">Library</a> › <a href="/books/">Books</a> › <a href="/books/#{b['cat']}">{esc(cat)}</a> › {esc(b['title'])}</p>
<div class="hero">
  <div>{cover_tag(b)}</div>
  <div>
    <h1>{esc(b['title'])}</h1>
    <p class="by">by <strong>{esc(b['author'])}</strong></p>
    <p class="facts">{esc(facts)}</p>
    <p class="lead">{esc(b['desc'])}</p>
    <div class="actions">
      <a class="btn primary" id="bcRead" href="{read}">Read online for free</a>
      <button type="button" class="btn ghost" id="bcDl" aria-expanded="false">Download {' · '.join(fmts)}</button>
      {audio_btn}
    </div>
    <div id="bcFormats" class="fmts" hidden></div>
    <div id="bcPlayer" class="player" hidden></div>
    <p class="free">Free · public domain · editions in {esc(lang_txt)}</p>
  </div>
</div>
<section class="card"><h2>Editions</h2><ul class="eds">{''.join(eds)}</ul></section>
{trailer_html(b)}
{('<section class="card"><h2>About the book</h2>' + readmore(about, 1) + '</section>') if about else ''}
{('<section class="card"><h2>About ' + esc(b["author"]) + '</h2>' + readmore([f'<p>{esc(x)}</p>' for x in auth_paras], 1) + '</section>') if auth_paras and b["author"] != "Anonymous" else ''}{f'<section class="card"><h2>Origins of the work</h2><p>{esc(ORIGINS[s])}</p></section>' if s in ORIGINS else ''}
{('<section class="card"><h2>How it begins</h2><blockquote>' + readmore([f'<p>{esc(p)}</p>' for p in op], 2 if sum(len(x) for x in op[:2]) < 1100 else 1) + f'</blockquote><p class="free" style="margin-top:12px"><a class="bcReadLink" href="{read}">Continue reading →</a></p></section>') if op else ''}
{('<section class="card"><h2>' + ('More by ' + esc(b['author']) + ' and similar classics' if same_author else 'You may also like') + '</h2><div class="grid">' + ''.join(mini(x) for x in related) + '</div></section>') if related else ''}
"""
    bc = {"slug": s, "ed": {l: MAN[s][l] for l in langs}, "audio": {l: {"u": a["url"], "d": a.get("duration", 0)} for l, a in audio.items() if a.get("url")}, "lang": langs[0]}
    body += '<script>const BC=' + json.dumps(bc, separators=(",", ":")) + ';</script>' + GATE_HTML + '<script>' + BOOK_JS + '</script>'
    ld = {"@context": "https://schema.org", "@type": "Book", "name": b["title"],
          "author": {"@type": "Person", "name": b["author"]},
          "url": f"{BASE}/books/{s}/", "inLanguage": langs, "genre": cat,
          "isAccessibleForFree": True, "bookFormat": "https://schema.org/EBook",
          "description": b["desc"], "publisher": {"@type": "Organization", "name": "BookClassics", "url": BASE}}
    if year_of(b): ld["datePublished"] = year_of(b)
    if b.get("pages"): ld["numberOfPages"] = b["pages"]
    if covers.get(s): ld["image"] = f"{BASE}/covers/{s}.jpg"
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Books", "item": f"{BASE}/books/"},
        {"@type": "ListItem", "position": 2, "name": b["title"], "item": f"{BASE}/books/{s}/"}]}
    os.makedirs(os.path.join(OUT, "books", s), exist_ok=True)
    open(os.path.join(OUT, "books", s, "index.html"), "w", encoding="utf-8").write(
        shell(title_tag, desc, f"/books/{s}/", body, [ld, crumbs], f"/covers/{s}.jpg" if covers.get(s) else None))
    urls.append((f"/books/{s}/", "0.8"))

# Page « tous les livres »
secs = []
for c in data["cats"]:
    lst = [b for b in books if b["cat"] == c["slug"]]
    if not lst: continue
    lst.sort(key=lambda b: b["title"].lower().removeprefix("the "))
    secs.append(f'<section class="card" id="{c["slug"]}"><h2>{esc(c["label"])} <span class="free">({len(lst)})</span></h2><div class="grid">{"".join(mini(b) for b in lst)}</div></section>')
body = f"""<p class="crumbs"><a href="/">Library</a> › Books</p>
<h1>All books</h1>
<p class="lead">{len(books)} great classics in the public domain, free to read online, download in EPUB, PDF, TXT or HTML, and often to listen to as audiobooks. Editions in English, French, Spanish, German, Italian, Portuguese and Swedish.</p>
<p class="free">{' · '.join(f'<a href="#{c["slug"]}">{esc(c["label"])}</a>' for c in data["cats"])}</p>
{''.join(secs)}"""
os.makedirs(os.path.join(OUT, "books"), exist_ok=True)
open(os.path.join(OUT, "books", "index.html"), "w", encoding="utf-8").write(
    shell("All books — free public-domain classics | BookClassics",
          f"Browse {len(books)} free classic books: novels, adventure, drama, poetry, philosophy and children's classics to read online, download or listen to.",
          "/books/", body))

sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, p in urls:
    sm.append(f"  <url><loc>{BASE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority></url>")
sm.append("</urlset>")
open(os.path.join(OUT, "sitemap.xml"), "w").write("\n".join(sm) + "\n")
open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")
print(len(books), "pages livres,", sum(1 for v in covers.values() if v), "couvertures,", len(urls), "adresses dans le sitemap")
