/* The dashboard manifest remains the single source for four flags and six gauges. */
(function(){
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const arrow='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg>';
 function draw(data){
  const date=new Date(data.generated+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
  document.querySelector('.snapshot-button span').textContent=date;
  document.querySelector('#status-sheet .sheet-top>span').textContent='Source records: '+date;
  const flags=data.attention.slice(0,4);
  document.querySelector('.attention-button strong').textContent=flags.length;
  document.querySelector('.attention-button').setAttribute('aria-label',`Open ${flags.length} things to check`);
  document.querySelector('.flag-list').innerHTML=flags.map(f=>{const room=data.rooms.find(r=>f.href.startsWith(r.href));return `<a class="flag" href="${esc(f.href)}"><span class="flag-dot" aria-hidden="true"></span><span class="flag-title">${esc(f.label)}</span><span class="flag-origin">${esc(room?.label||'Source record')} · ${date}</span>${arrow}</a>`}).join('');
  document.querySelector('[data-status="flags"] .sheet-description').textContent='Four open loops from the recorded snapshot.';
  document.querySelector('[data-status="figures"] .sheet-description').textContent='Six stored figures · '+date+'.';
  document.querySelector('.metrics').innerHTML=data.kpis.slice(0,6).map(k=>{let value=k.value,label=k.label,delta=k.delta,note=k.note;if(k.live==='hearing'){const h=data.next.find(x=>/hearing/i.test(x.label));if(h){value=new Date(h.date+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric'});label='Recorded hearing';delta='Check current logistics in the room'}}if(k.href==='/the-ledger/'){delta='Partial close · Amazon estimate';note+=' · Amazon August is estimated; later payments remain separate.'}return `<a class="metric" href="${esc(k.href)}" aria-label="${esc(label+': '+value+'. '+note)}"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(delta)}</small></a>`}).join('');
  document.querySelector('.caveat').textContent='Source snapshot: '+date+'. Debt includes the Amazon estimate carried forward from August. Later payments are not fully confirmed. Open a room for the complete record.';
 }
 draw(FALLBACK);
 fetch('/data/console-status.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('Status unavailable');return r.json()}).then(draw).catch(()=>{});
})();
