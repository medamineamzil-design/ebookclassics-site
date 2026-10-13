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


/* BookClassics destination preferences — 2026-10-12. Production stays gated. */
(()=>{'use strict';
const markets=[['GB','Royaume-Uni'],['US','États-Unis'],['IE','Irlande'],['NL','Pays-Bas'],['CA','Canada'],['AU','Australie'],['FR','France'],['DE','Allemagne'],['ES','Espagne'],['IT','Italie'],['DK','Danemark'],['LU','Luxembourg'],['EE','Estonie'],['NZ','Nouvelle-Zélande'],['MY','Malaisie'],['PH','Philippines'],['KE','Kenya'],['NG','Nigeria']];
window.bookclassicsMarketPreferences=Object.freeze({countries:markets.map(([code])=>code),excluded:['MA'],suppliers:['lulu','bookvault'],pricing:'fixed-delivered-price-per-title-and-binding',productionReady:false});
function applyCountries(){
 document.querySelectorAll('#bcPrintForm input[name="country_code"]').forEach(input=>{
  const select=document.createElement('select');select.name='country_code';select.required=true;select.setAttribute('aria-label','Pays de livraison');
  const empty=document.createElement('option');empty.value='';empty.textContent='Choisir un pays';select.append(empty);
  markets.forEach(([code,name])=>{const option=document.createElement('option');option.value=code;option.textContent=name;select.append(option);});
  let saved='';try{saved=localStorage.getItem('bookclassics.deliveryCountry')||'';}catch{}
  select.value=markets.some(([code])=>code===saved)?saved:(input.value||'').toUpperCase();
  const label=input.closest('label');if(label?.firstChild?.nodeType===3)label.firstChild.textContent='Pays de livraison';
  input.replaceWith(select);
  select.addEventListener('change',()=>{try{localStorage.setItem('bookclassics.deliveryCountry',select.value);}catch{}select.dispatchEvent(new Event('input',{bubbles:true}));});
 });
}
applyCountries();new MutationObserver(applyCountries).observe(document.body,{childList:true,subtree:true});
})();


/* Approved launch-price announcement. Group promotions are not active at checkout. */
(()=>{'use strict';
function mount(){
if(document.getElementById('bcLaunchOffer'))return true;
if(!document.querySelector('header.site'))return false;
const css=document.createElement('style');css.textContent=`
#bcLaunchOffer{box-sizing:border-box;margin:18px auto;width:calc(100% - 32px);max-width:1280px;padding:22px 26px;border:1px solid #bb9b51;border-radius:16px;background:linear-gradient(115deg,#103c30,#235b44);color:#fff9e9;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr) auto;align-items:center;gap:24px;box-shadow:0 9px 24px #173b2514;font-family:system-ui,sans-serif}#bcLaunchOffer *{box-sizing:border-box}#bcLaunchOffer .bc-offer-kicker{font-size:10px;font-weight:750;letter-spacing:.15em;color:#e8ce92;margin:0 0 7px}#bcLaunchOffer h2{font-family:Georgia,serif;font-size:clamp(21px,2.4vw,30px);font-weight:400;line-height:1.2;margin:0;color:#fff9e9}#bcLaunchOffer .bc-offer-price{color:#f5d789;white-space:nowrap}#bcLaunchOffer .bc-offer-caption{font-size:12px;color:#e6eadd;margin:8px 0 0}#bcLaunchOffer .bc-offer-tiers{display:flex;gap:8px}#bcLaunchOffer .bc-offer-tier{flex:1;min-width:75px;text-align:center;border:1px solid #d4bb7c70;border-radius:10px;padding:9px 8px;background:#ffffff09}#bcLaunchOffer .bc-offer-tier small{display:block;font-size:11px;color:#e6eadd}#bcLaunchOffer .bc-offer-tier strong{display:block;color:#f5d789;font-size:24px;line-height:1.3}#bcLaunchOffer button{border:0;background:#f4d88f;color:#183c30;border-radius:999px;padding:13px 18px;font:700 13px system-ui;cursor:pointer;white-space:nowrap;box-shadow:0 3px 0 #b89749}#bcLaunchOffer button:hover{background:#ffe7ad;transform:translateY(-1px)}#bcLaunchOffer button:focus-visible,#bcLaunchPrices button:focus-visible{outline:3px solid #e2a83e;outline-offset:4px}
#bcLaunchPrices{box-sizing:border-box;width:calc(100% - 28px);max-width:780px;max-height:90vh;overflow:auto;border:1px solid #cbb982;border-radius:20px;padding:26px;background:#fffaf0;color:#203b30;font-family:system-ui,sans-serif;box-shadow:0 20px 80px #0005}#bcLaunchPrices::backdrop{background:#10291fbb}#bcLaunchPrices *{box-sizing:border-box}#bcLaunchPrices .bc-price-heading{display:flex;justify-content:space-between;align-items:start;gap:15px}#bcLaunchPrices h2{font:normal 29px/1.2 Georgia,serif;margin:0 0 12px}#bcLaunchPrices .bc-price-close{border:1px solid #d5c7a4;border-radius:50%;width:34px;height:34px;flex-shrink:0;background:transparent;color:#244535;font:22px system-ui;cursor:pointer}#bcLaunchPrices .bc-price-intro{font-size:14px;line-height:1.6;margin:0 0 18px}#bcLaunchPrices .bc-price-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}#bcLaunchPrices .bc-price-card{padding:16px;border:1px solid #e0d5bd;border-radius:12px;background:#fffdf8}#bcLaunchPrices .bc-price-card:first-child{border-color:#b79b52;background:#f5edda}#bcLaunchPrices .bc-price-card h3{font-size:14px;margin:0 0 9px;color:#244535}#bcLaunchPrices .bc-price-card p{margin:0;font-size:12px;color:#596353}#bcLaunchPrices .bc-price-card strong{display:block;margin-top:5px;font:26px Georgia,serif;color:#244535}#bcLaunchPrices .bc-price-promo{background:#173f30;color:#fff7df;border-radius:12px;padding:16px;margin:18px 0 12px;line-height:1.6;font-size:14px}#bcLaunchPrices .bc-price-promo strong{color:#f5d789}#bcLaunchPrices .bc-price-note{font-size:12px;line-height:1.6;color:#596353;margin:12px 0 0}@media(max-width:900px){#bcLaunchOffer{grid-template-columns:1fr 1fr;gap:16px}#bcLaunchOffer button{grid-column:1/-1;justify-self:start}}@media(max-width:560px){#bcLaunchOffer{grid-template-columns:1fr;padding:20px;gap:16px;margin:12px auto}#bcLaunchOffer h2{font-size:25px}#bcLaunchOffer button{width:100%}#bcLaunchPrices{padding:20px}#bcLaunchPrices .bc-price-grid{grid-template-columns:1fr 1fr;gap:8px}#bcLaunchPrices .bc-price-card{padding:12px}#bcLaunchPrices .bc-price-card strong{font-size:23px}}@media(prefers-reduced-motion:reduce){#bcLaunchOffer button:hover{transform:none}}@media print{#bcLaunchOffer,#bcLaunchPrices{display:none!important}}
`;document.head.append(css);
const offer=document.createElement('section');offer.id='bcLaunchOffer';offer.setAttribute('aria-label','BookClassics printed collections');
const dialog=document.createElement('dialog');dialog.id='bcLaunchPrices';dialog.setAttribute('aria-labelledby','bcLaunchPricesTitle');
const data=[['Classiques express','Express classics','9,99 €'],['Petits classiques','Short classics','11,99 €'],['Broché court et moyen','Short & medium paperbacks','15,90 USD'],['Broché long','Long paperbacks','21,90 USD'],['Couverture rigide classique','Classic hardbacks','27,90 USD'],['Couverture rigide longue','Long hardbacks','34,90 USD'],['Illustré noir et blanc · broché','B&W illustrated · paperback','19,90 USD'],['Illustré noir et blanc · rigide','B&W illustrated · hardback','29,90 USD'],['Illustré couleur · broché','Colour illustrated · paperback','29,90 USD'],['Collector couleur · rigide','Colour collector · hardback','39,90 USD']];
function draw(){
const fr=(document.getElementById('uiLangSelect')?.value||document.documentElement.lang||'EN').toUpperCase().startsWith('FR');
const t=fr?{k:'LA COLLECTION IMPRIMÉE · BIENTÔT',h:'Des classiques à garder.',from:'À partir de',caption:'À lire, à offrir, à partager.',group:'Vos offres groupées au lancement',book:'livres',cta:'Découvrir les éditions & prix',title:'Choisissez votre prochaine édition',intro:'Nos tarifs de lancement, à partir de :',promo:'2 livres : −10 % · 3 livres : −15 % · 4 livres et plus : −20 %',note:'Éditions imprimées et offres groupées en préparation. Prix de départ avant taxes ; disponibilité et conditions de livraison confirmées selon le titre et la destination avant paiement. Remises sur une même commande vers une même adresse, selon les règles applicables dans le pays. Les lectures numériques restent gratuites.',close:'Fermer'}:{k:'PRINT COLLECTION · COMING SOON',h:'Classics worth keeping.',from:'From',caption:'To read, to give, to share.',group:'Bundle offers at launch',book:'books',cta:'Explore editions & prices',title:'Find your next edition',intro:'Our launch prices, starting from:',promo:'2 books: −10% · 3 books: −15% · 4 or more: −20%',note:'Print editions and bundle offers are being prepared. Starting prices before tax; availability and delivery terms confirmed for the title and destination before payment. Discounts apply to one order delivered to one address, subject to local rules. Digital reading remains free.',close:'Close'};
offer.innerHTML=`<div><p class="bc-offer-kicker">${t.k}</p><h2>${t.h}<br><span class="bc-offer-price">${t.from} 9,99 €</span></h2><p class="bc-offer-caption">${t.caption}</p></div><div><p class="bc-offer-kicker">${t.group}</p><div class="bc-offer-tiers">${[[2,10],[3,15],['4+',20]].map(([n,p])=>`<div class="bc-offer-tier"><small>${n} ${t.book}</small><strong>−${p}%</strong></div>`).join('')}</div></div><button type="button" aria-haspopup="dialog">${t.cta} →</button>`;
dialog.innerHTML=`<div class="bc-price-heading"><h2 id="bcLaunchPricesTitle">${t.title}</h2><button type="button" class="bc-price-close" aria-label="${t.close}">×</button></div><p class="bc-price-intro">${t.intro}</p><div class="bc-price-grid">${data.map(([a,b,p])=>`<article class="bc-price-card"><h3>${fr?a:b}</h3><p>${t.from}<strong>${p}</strong></p></article>`).join('')}</div><div class="bc-price-promo"><strong>${t.group}</strong><br>${t.promo}</div><p class="bc-price-note">${t.note}</p>`;
offer.querySelector('button').onclick=()=>dialog.showModal();dialog.querySelector('button').onclick=()=>dialog.close();
}
const sharedHeader=document.querySelector('header.site');const offerWrap=document.createElement('div');offerWrap.id='bcLaunchOfferWrap';offerWrap.style.paddingTop='1px';sharedHeader.after(offerWrap);offerWrap.append(offer);document.body.append(dialog);draw();
function positionOffer(){const mode=getComputedStyle(sharedHeader).position;const bottom=sharedHeader.getBoundingClientRect().bottom+(mode==='absolute'?window.scrollY:0);offer.style.marginTop=(mode==='absolute'||mode==='fixed'?Math.ceil(bottom+16):18)+'px';}
positionOffer();window.addEventListener('load',positionOffer,{once:true});window.addEventListener('resize',positionOffer);if(window.ResizeObserver)new ResizeObserver(positionOffer).observe(sharedHeader);document.addEventListener('change',e=>{if(e.target.id==='uiLangSelect')draw()});
return true;
}
function start(){if(mount())return;const observer=new MutationObserver(()=>{if(mount())observer.disconnect()});observer.observe(document.body,{childList:true,subtree:true});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
