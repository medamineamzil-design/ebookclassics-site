import os,re,json,sys,time
root=sys.argv[1] if len(sys.argv)>1 else '.'
books={}
for d in sorted(os.listdir(root)):
    p=os.path.join(root,d)
    if d.startswith('.') or not os.path.isdir(p): continue
    for f in os.listdir(p):
        m=re.match(re.escape(d)+r'(?:-([a-z]{2}(?:-[a-z]{2})?))?\.(epub|pdf|txt|html)$',f)
        if m and os.path.getsize(os.path.join(p,f))>1000:
            books.setdefault(d,{}).setdefault(m.group(1) or 'en',[]).append(m.group(2))
for d in books:
    for l in list(books[d]):
        books[d][l]=sorted(books[d][l])
        if len(books[d][l])<4: del books[d][l]   # on ne vend que les editions completes (4 formats)
books={d:v for d,v in books.items() if v}
json.dump({'generated':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'books':books},open(os.path.join(root,'manifest.json'),'w'),indent=1,sort_keys=True)
print('manifest.json :',len(books),'livres,',sum(len(v) for v in books.values()),'editions')
