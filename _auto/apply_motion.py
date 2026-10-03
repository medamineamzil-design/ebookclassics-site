#!/usr/bin/env python3
"""BookClassics — nouvelle apparence animée des pages livres (/books/<slug>/).
Post-traitement idempotent des pages générées par build_books.py :
couverture en livre 3D, titre animé, sections qui apparaissent au défilement,
barre d'actions collée en bas sur téléphone, emplacements publicitaires réservés (vides tant
qu'AdSense n'est pas activé). Usage : python3 apply_motion.py <dossier du site ou des pages>"""
import os, re, sys

MARK = 'id="bc-motion"'
GSAP = ('<script defer src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/gsap.min.js"></script>\n'
        '<script defer src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/ScrollTrigger.min.js"></script>\n')

CSS = '''<style id="bc-motion">
body{overflow-x:clip}
.bk3d{position:relative;width:240px;aspect-ratio:2/3;transform-style:preserve-3d;perspective:1400px;margin-inline:auto}
.bk3d-in{position:absolute;inset:0;transform-style:preserve-3d;transform:rotateY(16deg);transition:transform .6s cubic-bezier(.2,.8,.2,1)}
.bk3d:hover .bk3d-in{transform:rotateY(4deg) translateY(-6px)}
.bk3d .cover{position:absolute;inset:0;width:100%;height:100%;transform:translateZ(12px);border-radius:3px 10px 10px 3px!important;box-shadow:0 2px 3px rgba(0,0,0,.3),18px 26px 40px rgba(22,19,15,.32)!important}
.bk3d-spine{position:absolute;top:0;bottom:0;left:0;width:24px;transform:rotateY(-90deg);transform-origin:left;background:#0d2a20}
.bk3d-pages{position:absolute;top:2%;bottom:2%;right:0;width:24px;transform:rotateY(90deg) translateZ(calc(100% - 12px));transform-origin:right;background:repeating-linear-gradient(90deg,#f4efe3 0 2px,#e2dccd 2px 3px);border-radius:2px}
.bk3d-shine{position:absolute;inset:0;transform:translateZ(13px);border-radius:3px 10px 10px 3px;pointer-events:none;background:linear-gradient(90deg,rgba(0,0,0,.28) 0,rgba(255,255,255,.18) 3%,rgba(0,0,0,0) 7%)}
@media (max-width:680px){.bk3d{width:180px}}
.hero h1 .bw{display:inline-block;overflow:hidden;vertical-align:top;padding-bottom:.06em}
.hero h1 .bw>span{display:inline-block}
.grid{perspective:1200px}
.grid a img{transition:transform .45s cubic-bezier(.2,.8,.2,1),box-shadow .45s}
.grid a:hover img{transform:rotateY(-10deg) translateY(-6px);box-shadow:0 18px 30px rgba(22,19,15,.25)}
.trailer .yt{position:relative;display:block;width:100%;max-width:760px;aspect-ratio:16/9;border:0;padding:0;border-radius:14px;overflow:hidden;cursor:pointer;background:#000}
.trailer .yt img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s cubic-bezier(.2,.8,.2,1)}
.trailer .yt:hover img{transform:scale(1.04)}
.yt-play{position:absolute;left:50%;top:50%;width:76px;height:76px;margin:-38px 0 0 -38px;border-radius:50%;background:#C8F27A;box-shadow:0 10px 30px rgba(0,0,0,.4);transition:transform .3s}
.trailer .yt:hover .yt-play{transform:scale(1.08)}
.yt-play::after{content:"";position:absolute;left:31px;top:24px;border-left:22px solid #16130F;border-top:14px solid transparent;border-bottom:14px solid transparent}
.yt-frame{width:100%;max-width:760px;aspect-ratio:16/9;border:0;border-radius:14px;display:block}
.bc-ad:empty{display:none}
.bc-ad:not(:empty){min-height:290px;margin:18px 0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.bc-bar{display:none}
@media (max-width:680px){
  .bc-bar{display:flex;gap:8px;position:sticky;bottom:0;z-index:30;margin:18px 0 0;border-radius:16px 16px 0 0;padding:10px 16px calc(10px + env(safe-area-inset-bottom,0px));
    background:color-mix(in srgb,var(--bg,#F6F3EC) 92%,transparent);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-top:1px solid rgba(0,0,0,.08)}
  .bc-bar .btn{flex:1;justify-content:center;text-align:center;padding:12px 10px}
}
</style>
'''

JS = '''<script>
(function(){
  // barre d'actions collée en bas (téléphone) : mêmes boutons que la page
  var read=document.getElementById('bcRead'), listen=document.getElementById('bcListen'), dl=document.getElementById('bcDl');
  var bar=document.querySelector('.bc-bar');
  if(bar && read){
    var a=document.createElement('a'); a.className='btn primary'; a.href=read.getAttribute('href'); a.textContent=(document.documentElement.lang||'en').indexOf('fr')===0?'Lire':'Read free';
    a.addEventListener('click',function(e){ e.preventDefault(); read.click(); });
    bar.appendChild(a);
    var other=listen||dl;
    if(other){ var b=document.createElement('button'); b.type='button'; b.className='btn ghost'; b.textContent=listen?'▶ Listen':'Download'; b.addEventListener('click',function(){ other.scrollIntoView({block:'center'}); other.click(); }); bar.appendChild(b); }
  }
  function boot(){
    if(!window.gsap||!window.ScrollTrigger) return;
    if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.registerPlugin(ScrollTrigger);
    var h=document.querySelector('.hero h1');
    if(h){ h.innerHTML=h.textContent.trim().split(/\\s+/).map(function(w){return '<span class="bw"><span>'+w.replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];})+'</span></span>';}).join(' ');
      gsap.from(h.querySelectorAll('.bw>span'),{yPercent:110,duration:.9,ease:'power4.out',stagger:.06}); }
    var bk=document.querySelector('.bk3d-in');
    if(bk){
      gsap.from(bk,{rotationY:80,x:-40,duration:1.4,ease:'expo.out'});
      if(matchMedia('(min-width: 681px)').matches)
        gsap.to(bk,{rotationY:30,rotationX:4,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:true}});
    }
    gsap.from('.hero .by, .hero .facts, .hero .lead, .hero .actions, .hero .free',{y:16,opacity:.2,duration:.7,stagger:.07,delay:.25,ease:'power2.out'});
    gsap.from('.eds li',{y:16,scale:.97,opacity:.2,duration:.5,stagger:.06,ease:'back.out(2)',scrollTrigger:{trigger:'.eds',start:'top 90%'}});
    gsap.utils.toArray('main > section.card').forEach(function(c){
      gsap.from(c,{y:40,opacity:.25,duration:.8,ease:'power3.out',scrollTrigger:{trigger:c,start:'top 88%'}});
    });
    gsap.from('.grid a',{y:40,opacity:.2,duration:.7,stagger:.06,ease:'power3.out',scrollTrigger:{trigger:'.grid',start:'top 88%'}});
    addEventListener('load',function(){ ScrollTrigger.refresh(); });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
</script>
'''


def patch(s):
    if MARK in s or '<div class="hero">' not in s:
        return s
    # couverture -> livre 3D
    s = re.sub(r'(<div class="hero">\s*<div>)(<img class="cover"[^>]*>)(</div>)',
               r'\1<div class="bk3d"><div class="bk3d-in"><div class="bk3d-spine"></div>\2<div class="bk3d-shine"></div><div class="bk3d-pages"></div></div></div>\3', s, count=1)
    # emplacements publicitaires (vides tant qu'AdSense n'est pas activé)
    m = re.search(r'<section class="card"><h2>About the book</h2>.*?</section>', s, re.S)
    if m:
        s = s[:m.end()] + '\n<div class="bc-ad" id="bcAd1"></div>' + s[m.end():]
    m = re.search(r'<section class="card"><h2>More by ', s)
    if m:
        s = s[:m.start()] + '<div class="bc-ad" id="bcAd2"></div>\n' + s[m.start():]
    # barre d'actions téléphone, à la fin du contenu principal
    i = s.rfind('</main>')
    if i > 0:
        s = s[:i] + '<div class="bc-bar" aria-label="Quick actions"></div>\n' + s[i:]
    s = s.replace('</head>', CSS + GSAP + '</head>', 1)
    i = s.rfind('</body>')
    s = s[:i] + JS + s[i:]
    return s


def main():
    root = sys.argv[1]
    n = 0
    for dp, _, files in os.walk(os.path.join(root, 'books') if os.path.isdir(os.path.join(root, 'books')) else root):
        for f in files:
            if f != 'index.html':
                continue
            p = os.path.join(dp, f)
            s = open(p, encoding='utf-8').read()
            t = patch(s)
            if t != s:
                open(p, 'w', encoding='utf-8').write(t)
                n += 1
    print('pages livres animées :', n)


if __name__ == '__main__':
    main()
