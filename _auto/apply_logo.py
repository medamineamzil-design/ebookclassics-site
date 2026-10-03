import sys, os, re, glob
root=sys.argv[1]
ICONS=('<link rel="icon" href="/favicon.ico" sizes="any">\n'
       '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">\n'
       '<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">\n'
       '<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
       '<meta name="theme-color" content="#2D49EC">\n')
OG=('<meta property="og:image" content="https://bookclassics.org/og-image.png">\n'
    '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
    '<meta name="twitter:card" content="summary_large_image">\n')
BRAND_CSS='<style id="bc-logo">a.brand::before{content:"";width:32px;height:32px;border-radius:9px;background:url(/icon-192.png) center/cover no-repeat !important;display:inline-block;flex:none;}</style>\n'
SPA_CSS=('<style id="bc-logo">header.site a.logo span.logo-mark3d{width:34px !important;height:34px !important;border-radius:9px;'
         'background:url(/icon-192.png) center/cover no-repeat !important;box-shadow:none !important;}'
         'header.site a.logo span.logo-mark3d *{display:none !important;}</style>\n')
def head_insert(s, block, anchor=None):
    if anchor and anchor in s:
        i=s.index(anchor)+len(anchor); return s[:i]+'\n'+block+s[i:].lstrip('\n')
    i=s.index('</head>'); return s[:i]+block+s[i:]
n=0
for p in glob.glob(os.path.join(root,'**/*.html'),recursive=True):
    s=open(p,encoding='utf-8').read(); o=s
    spa = os.path.relpath(p,root)=='index.html'
    if 'rel="icon"' not in s:
        if spa:
            s=s.replace('<meta name="robots" content="noindex">\n','')
            s=head_insert(s, ICONS+OG+SPA_CSS, '<link rel="canonical" href="https://bookclassics.org/">')
        else:
            add=ICONS
            if 'og:image' not in s: add+=OG
            if 'a.brand' in s: add+=BRAND_CSS
            s=head_insert(s, add)
    if s!=o: open(p,'w',encoding='utf-8').write(s); n+=1
print('modified',n)

# même passage : nouvelle apparence animée des pages livres (idempotent)
try:
    import subprocess as _sp
    _sp.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "apply_motion.py"), root], check=False)
except Exception as _e:
    print("animations non appliquées :", _e)
