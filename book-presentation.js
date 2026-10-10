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
