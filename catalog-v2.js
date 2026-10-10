/* Twelve-book catalogue. Artwork is decorative; controls remain live and localized. */
(function(){
'use strict';
const labels={
EN:['All books','All languages','All formats','Open'],FR:['Tous les livres','Toutes les langues','Tous les formats','Ouvrir'],ES:['Todos los libros','Todos los idiomas','Todos los formatos','Abrir'],PT:['Todos os livros','Todos os idiomas','Todos os formatos','Abrir'],PB:['Todos os livros','Todos os idiomas','Todos os formatos','Abrir'],AR:['جميع الكتب','جميع اللغات','جميع الصيغ','فتح'],ZH:['所有图书','所有语言','所有格式','打开'],ZT:['所有書籍','所有語言','所有格式','開啟'],JA:['すべての本','すべての言語','すべての形式','開く'],RU:['Все книги','Все языки','Все форматы','Открыть'],DE:['Alle Bücher','Alle Sprachen','Alle Formate','Öffnen'],SQ:['Të gjithë librat','Të gjitha gjuhët','Të gjitha formatet','Hap'],EU:['Liburu guztiak','Hizkuntza guztiak','Formatu guztiak','Ireki'],CA:['Tots els llibres','Totes les llengües','Tots els formats','Obre'],HI:['सभी पुस्तकें','सभी भाषाएँ','सभी प्रारूप','खोलें'],IT:['Tutti i libri','Tutte le lingue','Tutti i formati','Apri'],KO:['모든 도서','모든 언어','모든 형식','열기'],RO:['Toate cărțile','Toate limbile','Toate formatele','Deschide'],SR:['Све књиге','Сви језици','Сви формати','Отвори'],SV:['Alla böcker','Alla språk','Alla format','Öppna'],TR:['Tüm kitaplar','Tüm diller','Tüm biçimler','Aç'],UK:['Усі книги','Усі мови','Усі формати','Відкрити']};
function install(){
 const view=document.getElementById('view-catalog');if(!view||view.dataset.twelve)return;view.dataset.twelve='true';
 const bar=document.createElement('div');bar.className='catalog-twelve-bar';
 const heading=document.createElement('h1');bar.append(heading);
 function selector(id,change){const s=document.createElement('select');s.id=id;s.onchange=()=>{change(s.value);state.page=1;renderCatalog();renderCatBar()};bar.append(s);return s}
 const genre=selector('catalogGenre',v=>state.cat=v||null);
 const language=selector('catalogLanguage',v=>state.languages=new Set(v?[v]:[]));
 const format=selector('catalogFormat',v=>state.formats=new Set(v?[v]:[]));
 const sort=document.getElementById('sortSelect');bar.append(sort);view.prepend(bar);
 const words=()=>labels[state.uiLang]||labels.EN;
 function options(node,entries,value){node.replaceChildren();entries.forEach(([val,label])=>{const o=document.createElement('option');o.value=val;o.textContent=label;node.append(o)});node.value=value||''}
 function refresh(){
  const w=words();view.dir=state.uiLang==='AR'?'rtl':'ltr';heading.textContent=w[0];
  options(genre,[['',t('catalog.allGenres')],...CATEGORIES.map(c=>[c.slug,catLabel(c.slug)])],state.cat);
  const editions=typeof EDITIONS!=='undefined'?new Set(Object.values(EDITIONS).flatMap(e=>Object.keys(e))):null;
  options(language,[['',w[1]],...LANGUAGES.filter(l=>!editions||editions.has(l.iso.toLowerCase())).map(l=>[l.code,l.label])],[...state.languages][0]);
  options(format,[['',w[2]],...['EPUB','PDF','TXT','HTML'].map(f=>[f,f])],[...state.formats][0]);
  genre.setAttribute('aria-label',t('catalog.genre'));language.setAttribute('aria-label',t('catalog.language'));format.setAttribute('aria-label',t('catalog.format'));sort.setAttribute('aria-label',t('catalog.sortRelevance'));
  document.querySelectorAll('#catalogGrid>.card').forEach(card=>{
   card.classList.add('catalog-real-book');
   card.querySelectorAll('.title,.author').forEach(n=>{n.setAttribute('translate','no');n.dir='auto'});
   if(!card.querySelector('.catalog-open')){const button=document.createElement('span');button.className='catalog-open';card.querySelector('.info').append(button)}
   card.querySelector('.catalog-open').textContent=w[3];
   const title=card.querySelector('.title')?.textContent||'';card.setAttribute('aria-label',w[3]+' — '+title);
  });
  const pager=document.getElementById('catalogPagination'),buttons=[...pager.querySelectorAll('button')];
  // Keep the first/last pages and nearby pages; collapse long runs into ellipses.
  let gap=false;buttons.forEach((b,i)=>{if(i===0||i===buttons.length-1)return;const page=Number(b.textContent);const keep=page===1||page===buttons.length-2||Math.abs(page-state.page)<=1;
   if(!keep){if(!gap){const e=document.createElement('span');e.textContent='…';e.setAttribute('aria-hidden','true');b.before(e)}gap=true;b.remove()}else gap=false;
  });
 }
 const render=renderCatalog;renderCatalog=function(){const r=render.apply(this,arguments);refresh();return r};
 const lang=applyUILang;applyUILang=function(){const r=lang.apply(this,arguments);refresh();return r};
 renderCatalog();
}
window.addEventListener('load',()=>requestAnimationFrame(install));
})();
