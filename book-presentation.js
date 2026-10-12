/* One shared cover renderer for current and future book cards. */
(()=>{'use strict';
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
'Frankenstein':[519,687,190,191],
'The Great Gatsby':[823,687,194,191],
'The Adventures of Sherlock Holmes':[1125,688,196,190]
};

function decorate(book,title){
 if(book.dataset.hardcoverReady)return;
 book.dataset.hardcoverReady='true';book.classList.add('bc-hardcover');
 const crop=referenceBooks[title];
 if(crop){const [x,y,w,h]=crop;book.classList.add('bc-reference');book.style.setProperty('--bc-size',`${1536/w*100}% ${1024/h*100}%`);book.style.setProperty('--bc-position',`${x/(1536-w)*100}% ${y/(1024-h)*100}%`);}
}
function scan(){
 document.querySelectorAll('.book3d:not([data-hardcover-ready])').forEach(book=>{
 const card=book.closest('.card,.book-detail');
 const title=card?.querySelector('.title,h1')?.textContent.trim()||book.querySelector('img')?.alt.replace(/ cover$/,'')||'';
 decorate(book,title);
 });
 document.querySelectorAll('.bk3d-in:not([data-hardcover-ready])').forEach(book=>decorate(book,document.querySelector('main h1')?.textContent.trim()||''));
 document.querySelectorAll('main .grid a img:not(.cover-img):not([data-hardcover-image])').forEach(img=>{
 if(img.closest('.bc-hardcover,.book3d,.bk3d'))return;
 img.dataset.hardcoverImage='true';const frame=document.createElement('span');frame.className='bc-cover-frame';img.before(frame);frame.append(img);
 const title=img.closest('a')?.querySelector('strong,b')?.textContent.trim()||img.alt.replace(/^Cover of /,'').split(' by ')[0];decorate(frame,title);
 });
}
let queued=false;function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;scan()})}
function start(){scan();new MutationObserver(schedule).observe(document.body,{subtree:true,childList:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();

/* Editorial detail layout; preserves existing checkout handlers and availability. */
(()=>{'use strict';
function present(){
 const hero=document.querySelector('main .hero');if(!hero||!hero.querySelector('.bk3d'))return;
 document.body.classList.add('bc-editorial');
 const info=hero.children[1];if(!info)return;
 if(!info.querySelector('.preview-kicker')){const k=document.createElement('p');k.className='preview-kicker';k.textContent='BookClassics · The classics collection';info.prepend(k)}
 const facts=info.querySelector('.facts');if(facts&&!facts.querySelector('.preview-tag')){const values=facts.textContent.split(' · ');facts.replaceChildren(...values.map(v=>{const tag=document.createElement('span');tag.className='preview-tag';tag.textContent=v;return tag}))}
 const buy=info.querySelector('#bcPrint');
 if(buy&&!buy.querySelector('.preview-buy-copy')){
 const original=buy.textContent;buy.setAttribute('aria-label',original);
 const icon=document.createElement('span');icon.className='preview-book-icon';icon.setAttribute('aria-hidden','true');
 const copy=document.createElement('span');copy.className='preview-buy-copy';
 const title=document.createElement('span');title.textContent='Commander le livre';
 const sub=document.createElement('span');sub.className='preview-buy-sub';sub.textContent='Broché ou relié · format 6 × 9 · mode test';copy.append(title,sub);
 const arrow=document.createElement('span');arrow.className='preview-buy-arrow';arrow.setAttribute('aria-hidden','true');arrow.textContent='→';buy.replaceChildren(icon,copy,arrow);
 }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',present);else present();
new MutationObserver(()=>{if(!document.body.classList.contains('bc-editorial')||document.querySelector('#bcPrint:not(:has(.preview-buy-copy))'))present()}).observe(document.documentElement,{childList:true,subtree:true});
})();
