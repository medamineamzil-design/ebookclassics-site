/* Twelve-book catalogue. Artwork is decorative; controls remain live and localized. */
(function(){
'use strict';
const referenceBooks={
'The Count of Monte Cristo':[213,131,194,185],
'Pride and Prejudice':[519,132,187,184],
'Treasure Island':[823,132,193,184],
'Dracula':[1126,132,195,185],
'Jane Eyre':[213,407,195,190],
'Moby-Dick':[519,408,189,189],
'The Picture of Dorian Gray':[823,408,194,190],
"Alice's Adventures in Wonderland":[1126,408,195,190],
'The Odyssey':[212,687,196,190],
'The Great Gatsby':[823,687,194,191],
'The Adventures of Sherlock Holmes':[1125,688,196,190]
};
const labels={
EN:['All books','All languages','All formats','Open'],FR:['Tous les livres','Toutes les langues','Tous les formats','Ouvrir'],ES:['Todos los libros','Todos los idiomas','Todos los formatos','Abrir'],PT:['Todos os livros','Todos os idiomas','Todos os formatos','Abrir'],PB:['Todos os livros','Todos os idiomas','Todos os formatos','Abrir'],AR:['جميع الكتب','جميع اللغات','جميع الصيغ','فتح'],ZH:['所有图书','所有语言','所有格式','打开'],ZT:['所有書籍','所有語言','所有格式','開啟'],JA:['すべての本','すべての言語','すべての形式','開く'],RU:['Все книги','Все языки','Все форматы','Открыть'],DE:['Alle Bücher','Alle Sprachen','Alle Formate','Öffnen'],SQ:['Të gjithë librat','Të gjitha gjuhët','Të gjitha formatet','Hap'],EU:['Liburu guztiak','Hizkuntza guztiak','Formatu guztiak','Ireki'],CA:['Tots els llibres','Totes les llengües','Tots els formats','Obre'],HI:['सभी पुस्तकें','सभी भाषाएँ','सभी प्रारूप','खोलें'],IT:['Tutti i libri','Tutte le lingue','Tutti i formati','Apri'],KO:['모든 도서','모든 언어','모든 형식','열기'],RO:['Toate cărțile','Toate limbile','Toate formatele','Deschide'],SR:['Све књиге','Сви језици','Сви формати','Отвори'],SV:['Alla böcker','Alla språk','Alla format','Öppna'],TR:['Tüm kitaplar','Tüm diller','Tüm biçimler','Aç'],UK:['Усі книги','Усі мови','Усі формати','Відкрити']};
function install(){
 const view=document.getElementById('view-catalog');if(!view||view.dataset.twelve)return;view.dataset.twelve='true';view.dataset.daylight='true';
 const bar=document.createElement('div');bar.className='catalog-twelve-bar';
 const headingWrap=document.createElement('div');headingWrap.className='catalog-heading';
 const heading=document.createElement('h1'),subtitle=document.createElement('p');subtitle.className='catalog-subtitle';headingWrap.append(heading,subtitle);bar.append(headingWrap);
 function selector(id,change){const s=document.createElement('select');s.id=id;s.onchange=()=>{change(s.value);state.page=1;renderCatalog();renderCatBar()};bar.append(s);return s}
 const genre=selector('catalogGenre',v=>state.cat=v||null);
 const language=selector('catalogLanguage',v=>state.languages=new Set(v?[v]:[]));
 const format=selector('catalogFormat',v=>state.formats=new Set(v?[v]:[]));
 const sort=document.getElementById('sortSelect');bar.append(sort);view.prepend(bar);
 const words=()=>labels[state.uiLang]||labels.EN;
 const copy=()=>window.BC_CATALOG_COPY[state.uiLang]||window.BC_CATALOG_COPY.EN;
 const note=document.createElement('p');note.className='catalog-delivery-note';
 const offer=document.createElement('section');offer.className='catalog-collection-offer';
 offer.innerHTML='<div class="catalog-offer-heading"><span class="catalog-offer-ornament" aria-hidden="true">❧</span><h2></h2></div><div class="catalog-offer-tiers">'+[10,15,20].map((n,i)=>'<div><span data-tier="'+i+'"></span><strong>−'+n+'<small>%</small></strong></div>').join('')+'</div><div class="catalog-offer-status"></div><p class="catalog-offer-terms"></p>';
 view.append(offer,note);
 let printPrices=null,priceFailed=false;
 const money=value=>new Intl.NumberFormat(({PB:'pt-BR',ZT:'zh-TW',ZH:'zh-CN',EN:'en-US'})[state.uiLang]||state.uiLang.toLowerCase(),{style:'currency',currency:'USD',currencyDisplay:'symbol'}).format(value);
 // Same availability gate and USD price schedule as the existing shop. No estimated title prices are published here.
 fetch('https://raw.githubusercontent.com/medamineamzil-design/ebookclassics-files/main/print.json',{cache:'no-store'})
 .then(response=>{if(!response.ok)throw Error('Price catalogue unavailable');return response.json()})
 .then(data=>{printPrices={};for(const [slug,item] of Object.entries(data)){if(item&&item.bv_interior&&item.bv_cover&&(item.price_usd||item.bv_pages)&&!slug.endsWith('-hardcover')){const value=Number(item.price_usd||[[64,11.9],[120,13.9],[250,15.9],[400,18.9],[550,21.9],[750,24.9],[900,27.9],[1e9,32.9]].find(tier=>item.bv_pages<=tier[0])[1]);if(Number.isFinite(value)&&value>0)printPrices[slug]=value;}}refresh()})
 .catch(()=>{priceFailed=true;printPrices={};refresh()});
 const paged=new WeakSet();
 function options(node,entries,value){node.replaceChildren();entries.forEach(([val,label])=>{const o=document.createElement('option');o.value=val;o.textContent=label;node.append(o)});node.value=value||''}
 function refresh(){
  const w=words(),c=copy();view.dir=state.uiLang==='AR'?'rtl':'ltr';heading.textContent=w[0];subtitle.textContent=c.subtitle;
  note.textContent=c.note;offer.setAttribute('aria-label',c.collection);offer.querySelector('h2').textContent=c.collection;
  offer.querySelector('.catalog-offer-status').textContent=c.upcoming;offer.querySelector('.catalog-offer-terms').textContent=c.terms;
  offer.querySelectorAll('[data-tier]').forEach((node,i)=>node.textContent=[c.two,c.three,c.four][i]);
  const cart=document.getElementById('bcCartOpen');if(cart){const label=cart.querySelector('.bc-cart-label');if(label)label.textContent=c.cart;cart.setAttribute('aria-label',c.cart+' · '+(cart.querySelector('.bc-cart-count')?.textContent||'0'));}
  options(genre,[['',t('catalog.allGenres')],...CATEGORIES.map(c=>[c.slug,catLabel(c.slug)])],state.cat);
  const editions=typeof EDITIONS!=='undefined'?new Set(Object.values(EDITIONS).flatMap(e=>Object.keys(e))):null;
  options(language,[['',w[1]],...LANGUAGES.filter(l=>!editions||editions.has(l.iso.toLowerCase())).map(l=>[l.code,l.label])],[...state.languages][0]);
  options(format,[['',w[2]],...['EPUB','PDF','TXT','HTML'].map(f=>[f,f])],[...state.formats][0]);
  genre.setAttribute('aria-label',t('catalog.genre'));language.setAttribute('aria-label',t('catalog.language'));format.setAttribute('aria-label',t('catalog.format'));sort.setAttribute('aria-label',t('catalog.sortRelevance'));
  document.querySelectorAll('#catalogGrid>.card').forEach(card=>{
   card.classList.add('catalog-real-book');
   card.querySelectorAll('.title,.author').forEach(n=>{n.setAttribute('translate','no');n.dir='auto'});
   if(!card.querySelector('.catalog-open')){const button=document.createElement('span');button.className='catalog-open';card.querySelector('.info').append(button)}
   card.querySelector('.catalog-open').textContent=c.choose;
   const title=card.querySelector('.title')?.textContent||'';
   const source=card.querySelector('img')?.getAttribute('src')||'';
   const slug=source.split('/').pop()?.replace(/\.[^.]+$/,'');
   let price=card.querySelector('.catalog-starting-price');if(!price){price=document.createElement('span');price.className='catalog-starting-price';card.querySelector('.author').after(price)}
   const value=printPrices?.[slug];
   price.replaceChildren();
   if(value){const prefix=document.createElement('span'),amount=document.createElement('bdi');prefix.textContent=c.from+' ';amount.textContent=money(value);price.append(prefix,amount);price.classList.remove('catalog-price-pending');price.title=c.note;}
   else{price.textContent=!printPrices?c.loading:(priceFailed?c.unavailable:c.soon);price.classList.add('catalog-price-pending');price.removeAttribute('title');}
   card.querySelector('.title').title=title;card.querySelector('.author').title=card.querySelector('.author').textContent;
   // Keep the approved icy Frankenstein artwork, including after the shared cover renderer runs.
   if(title==='Frankenstein')card.classList.add('catalog-icy-cover');
   const crop=referenceBooks[title];
   if(crop){
    const [x,y,width,height]=crop,book=card.querySelector('.book3d');
    card.classList.add('catalog-reference-book');
    book.style.setProperty('--reference-size',`${1536/width*100}% ${1024/height*100}%`);
    book.style.setProperty('--reference-position',`${x/(1536-width)*100}% ${y/(1024-height)*100}%`);
   }
   card.setAttribute('aria-label',c.choose+' — '+title);
  });
  const count=document.querySelectorAll('#catalogGrid>.card').length;view.style.setProperty('--catalog-desktop-rows',Math.max(1,Math.ceil(count/3)));view.style.setProperty('--catalog-mobile-rows',Math.max(1,Math.ceil(count/2)));view.classList.toggle('catalog-is-empty',count===0);
  const pager=document.getElementById('catalogPagination'),buttons=[...pager.querySelectorAll('button')];
  if(!buttons.length||paged.has(buttons[0]))return;paged.add(buttons[0]);
  // Keep the first/last pages and nearby pages; collapse long runs into ellipses.
  let gap=false;buttons.forEach((b,i)=>{if(i===0||i===buttons.length-1)return;const page=Number(b.textContent);const keep=page===1||page===buttons.length-2||Math.abs(page-state.page)<=1;
   if(!keep){if(!gap){const e=document.createElement('span');e.textContent='…';e.setAttribute('aria-hidden','true');b.before(e)}gap=true;b.remove()}else gap=false;
  });
 }
 const render=renderCatalog;renderCatalog=function(){const r=render.apply(this,arguments);refresh();return r};
 const lang=applyUILang;applyUILang=function(){const r=lang.apply(this,arguments);refresh();return r};
 document.addEventListener('change',event=>{if(event.target.id==='uiLangSelect')requestAnimationFrame(refresh)});
 renderCatalog();
}
window.addEventListener('load',()=>requestAnimationFrame(install));
})();
