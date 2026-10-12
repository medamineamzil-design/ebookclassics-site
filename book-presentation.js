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

/* Frankenstein print test. No payment credentials in the browser. */
(()=>{'use strict';
if(location.pathname.replace(/\/$/,'')!=='/books/frankenstein')return;
if(document.getElementById('bcPrint'))return;
const API='https://bookclassics-shop.medamine-amzil.workers.dev';
const STORE='bc-frankenstein-test-order';
const style=document.createElement('style');
style.textContent=`#bcPrintDialog{border:0;border-radius:18px;max-width:620px;width:calc(100% - 32px);max-height:90vh;padding:24px;color:#29221a;background:#fffdf8;box-sizing:border-box}#bcPrintDialog::backdrop{background:#0009}#bcPrintDialog *{box-sizing:border-box}#bcPrintDialog h2{margin:0 0 12px}#bcPrintDialog .print-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}#bcPrintDialog label{display:block;font-size:14px;font-weight:600}#bcPrintDialog select{display:block;width:100%;padding:10px;margin:5px 0 18px;border:1px solid #b9b1a4;border-radius:6px;font:inherit;background:white;color:#29221a}#bcPrintDialog input{display:block;width:100%;padding:10px;margin-top:5px;border:1px solid #b9b1a4;border-radius:6px;font:inherit;background:white;color:#29221a}#bcPrintDialog .print-wide{grid-column:1/-1}#bcPrintDialog button{cursor:pointer;padding:12px 18px;border:1px solid #67553c;border-radius:8px;font:inherit;background:#fffdf8;color:#29221a}#bcPrintDialog button:disabled{opacity:.5;cursor:wait}#bcPrintDialog .print-primary{background:#3f3629;color:white}#bcPrintDialog .print-notice{padding:12px;border:1px solid #e4cd92;border-radius:8px;background:#fff4d9}#bcPrintDialog .print-controls{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}#bcPrintDialog [hidden]{display:none!important}#bcPrintMessage{white-space:pre-line;margin-top:16px}#bcPrintDialog :focus-visible{outline:3px solid #3063a3;outline-offset:3px}@media(max-width:480px){#bcPrintDialog .print-grid{grid-template-columns:1fr}}
`;
document.head.append(style);
const btn=document.createElement('button');btn.type='button';btn.className='btn ghost';btn.id='bcPrint';btn.textContent='Commander un exemplaire — TEST';
document.querySelector('.hero .actions')?.append(btn);
const dialog=document.createElement('dialog');dialog.id='bcPrintDialog';dialog.setAttribute('aria-labelledby','bcPrintTitle');
dialog.innerHTML=`<h2 id="bcPrintTitle">Frankenstein · exemplaire imprimé</h2><p>Édition test · 182 pages · 15,24 × 22,86 cm · broché ou couverture rigide · intérieur noir et blanc.</p><p class="print-notice"><strong>Mode TEST</strong> — aucun débit réel, aucune impression ni livraison. Utilisez une adresse fictive et un compte PayPal Sandbox.</p><form id="bcPrintForm"><label>Reliure<select id="bcPrintEdition"><option value="frankenstein">Broché</option><option value="frankenstein-hardcover">Couverture rigide — Hardcover</option></select></label><div class="print-grid"><label class="print-wide">Nom complet<input name="name" required maxlength="120" autocomplete="off"></label><label class="print-wide">Adresse<input name="street1" required maxlength="120" autocomplete="off"></label><label class="print-wide">Complément d’adresse<input name="street2" maxlength="120" autocomplete="off"></label><label>Ville<input name="city" required maxlength="120" autocomplete="off"></label><label>Code postal<input name="postcode" required maxlength="120" autocomplete="off"></label><label>Pays — code à 2 lettres<input name="country_code" required pattern="[A-Za-z]{2}" maxlength="2" placeholder="US, FR, MA…" autocomplete="off"></label><label>État / région — code<input name="state_code" maxlength="120" placeholder="NC pour notre test US" autocomplete="off"></label><label>Téléphone test<input name="phone_number" required maxlength="120" type="tel" autocomplete="off"></label><label>Email test<input name="email" required maxlength="120" type="email" autocomplete="off"></label></div><div class="print-controls"><button type="button" id="bcPrintExample">Remplir l’adresse fictive</button><button type="submit" class="print-primary" id="bcPrintQuote">Calculer le total</button></div></form><p id="bcPrintMessage" role="status" aria-live="polite"></p><div class="print-controls"><button type="button" class="print-primary" id="bcPrintPay" hidden>Payer avec PayPal — TEST</button><button type="button" id="bcPrintTrack" hidden>Vérifier la commande test</button><button type="button" id="bcPrintClose">Fermer</button></div>`;
document.body.append(dialog);
const $=id=>document.getElementById(id),form=$('bcPrintForm'),msg=$('bcPrintMessage'),pay=$('bcPrintPay'),track=$('bcPrintTrack');
let quoted=null,busy=false,order=null;
async function api(path,data){const response=await fetch(API+path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:undefined,body:data?JSON.stringify(data):undefined,cache:'no-store'});const result=await response.json();if(!response.ok)throw Error(result.error||'Service indisponible. Réessayez plus tard.');return result;}
async function sandbox(){const conf=await api('/config');if($('bcPrintEdition').value==='frankenstein-hardcover'&&conf.hardcover!==true)throw Error('La version rigide attend la mise à jour du serveur.');if(conf.sandbox!==true)throw Error('Le paiement test est indisponible : le serveur doit être en mode Sandbox.');}
function lock(value){busy=value;form.querySelectorAll('input,select,button').forEach(el=>el.disabled=value);pay.disabled=value;track.disabled=value;}
function remember(value){order=value;try{sessionStorage.setItem(STORE,JSON.stringify(value));}catch{}}
function restore(){try{return JSON.parse(sessionStorage.getItem(STORE)||'null');}catch{return null;}}
function address(){return Object.fromEntries(Array.from(new FormData(form),([k,v])=>[k,String(v).trim()]));}
btn.onclick=()=>dialog.showModal();$('bcPrintClose').onclick=()=>dialog.close();
form.oninput=()=>{quoted=null;pay.hidden=true;msg.textContent='Adresse modifiée : recalculez le total avant de payer.';};
$('bcPrintExample').onclick=()=>{const example={name:'Test BookClassics',street1:'123 Test Street',street2:'',city:'Raleigh',postcode:'27601',country_code:'US',state_code:'NC',phone_number:'2025550100',email:'test@example.com'};Object.entries(example).forEach(([key,value])=>form.elements.namedItem(key).value=value);quoted=null;pay.hidden=true;msg.textContent='Adresse fictive remplie. Vous pouvez calculer le total.';};
form.onsubmit=async event=>{event.preventDefault();if(busy)return;const addr=address();lock(true);msg.textContent='Calcul de l’impression et de la livraison…';pay.hidden=true;try{await sandbox();const quote=await api('/quote',{slug:$('bcPrintEdition').value,address:addr});quoted={addr,slug:$('bcPrintEdition').value,price:quote.price,currency:quote.currency};msg.textContent=`${$('bcPrintEdition').selectedOptions[0].textContent}\nTotal test : ${quote.price} ${quote.currency}\nImpression et livraison incluses pour cette adresse.\nAucun montant réel ne sera débité.`;pay.hidden=false;}catch(e){msg.textContent=e.message;}finally{lock(false);}};
pay.onclick=async()=>{if(busy||!quoted)return;lock(true);msg.textContent='Ouverture du paiement PayPal Sandbox…';try{await sandbox();const created=await api('/create',{slug:quoted.slug,address:quoted.addr});const dest=new URL(created.approval_url);if(dest.protocol!=='https:'||dest.hostname!=='www.sandbox.paypal.com')throw Error('Lien de paiement test invalide.');remember({id:created.id,phase:'created'});location.assign(dest.href);}catch(e){msg.textContent=e.message;lock(false);}};
async function showStatus(){if(!order?.id)return;lock(true);try{const result=await api('/status',{id:order.id});const accepted=(result.line_items||[]).some(item=>item.status?.name==='ACCEPTED');msg.textContent=`Commande test : ${order.id}\nStatut Lulu : ${result.status?.name||result.status||'en attente'}.`+(accepted?'\nLulu a accepté le livre.':'')+'\nMode Sandbox : aucun paiement réel ni impression.';}catch(e){msg.textContent=e.message;}finally{lock(false);}}
track.onclick=showStatus;
const params=new URLSearchParams(location.search),returned=params.get('print_test');
if(returned){order=restore();dialog.showModal();form.hidden=true;history.replaceState(null,'',location.pathname);if(returned==='cancel'){msg.textContent='Paiement test annulé. Aucun paiement confirmé.';form.hidden=false;}else if(!order?.id||params.get('token')!==order.id){msg.textContent='Retour PayPal non reconnu. Recommencez le test depuis cette page.';form.hidden=false;}else if(order.phase==='sent'){track.hidden=false;showStatus();}else{lock(true);msg.textContent='Vérification du paiement test et transmission à Lulu…';(async()=>{try{await sandbox();const result=await api('/capture',{id:order.id});if(!result.ok)throw Error('Paiement test confirmé, mais transmission à Lulu non confirmée. Ne recommencez pas le paiement.');remember({id:order.id,phase:'sent'});msg.textContent=`Paiement test confirmé. Commande transmise à Lulu.\nRéférence : ${order.id}\nAucun paiement réel ni impression.`;track.hidden=false;}catch(e){msg.textContent=e.message+'\nRéférence : '+order.id;}finally{lock(false);}})();}}
})();

