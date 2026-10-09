(() => {
  'use strict';
  const data = window.HearingPaths;
  if (!data) {
    document.querySelector('.hp').innerHTML = '<section class="hp-section"><div class="hp-heading"><h2>The case map could not load.</h2></div><p>Please <a href="/hearing-room/">reload the Hearing Room</a> to try again.</p></section>';
    return;
  }
  const $ = (s) => document.querySelector(s);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const refs = (ids = []) => ids.map(id => `<button type="button" class="hp-ref" data-source="${esc(id)}" aria-label="Read source ${esc(id)}">[${esc(id)}]</button>`).join(' ');
  const paragraph = item => `<p>${esc(item.text)} ${refs(item.refs)}</p>`;
  let track = 'dv', perspective = 'you', choice = 0;
  function renderMap() {
    const lane = data.tracks[track], paths = lane.paths[perspective], selected = paths[choice];
    $('.hp-map').dataset.track = track;
    document.querySelectorAll('#track-controls button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.track === track)));
    document.querySelectorAll('#perspective-controls button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.perspective === perspective)));
    $('#map-caption').textContent = lane.caption;
    $('#process-stages').innerHTML = `<p class="hp-stage-caption">${esc(lane.stageCaption)}</p><ol class="hp-stages">${lane.stages.map(s=>`<li><span>${esc(s.label)}</span><small>${esc(s.note)}</small></li>`).join('')}</ol>`;
    $('#route-origin').innerHTML = `<span class="hp-route-label">The recorded position</span><h3>${esc(lane.title)}</h3><p>${esc(lane.current)} ${refs(lane.refs)}</p>`;
    $('#route-choices').innerHTML = paths.map((p,i) => `<button type="button" class="hp-choice" data-choice="${i}" aria-pressed="${i === choice}" aria-controls="route-detail"><span><strong>${esc(p.title)}</strong><small>${esc(p.subtitle)}</small></span><span aria-hidden="true">${i===choice?'↗':'+'}</span></button>`).join('');
    $('#route-destination').innerHTML = `<span class="hp-route-label">A possible next state</span><h3>${esc(selected.destination)}</h3><p>${esc(selected.outcome)}</p>`;
    $('#route-detail').innerHTML = selected.details.map(d => `<div><h4>${esc(d.label)}</h4>${paragraph(d)}</div>`).join('');
  }
  $('#track-controls').addEventListener('click', e => { const b=e.target.closest('button[data-track]'); if(!b)return;track=b.dataset.track;choice=0;renderMap(); });
  $('#perspective-controls').addEventListener('click', e => { const b=e.target.closest('button[data-perspective]');if(!b)return;perspective=b.dataset.perspective;choice=0;renderMap(); });
  $('#route-choices').addEventListener('click', e => { const b=e.target.closest('button[data-choice]');if(!b)return;choice=Number(b.dataset.choice);renderMap();$(`[data-choice="${choice}"]`).focus({preventScroll:true}); });
  $('#intro-copy').innerHTML = esc(data.intro.text)+' '+refs(data.intro.refs);
  $('#case-summary').innerHTML = data.summary.map(s=>`<a href="#paths" data-track-link="${esc(s.track)}"><i aria-hidden="true"></i><span><strong>${esc(s.title)}</strong><small>${esc(s.text)}</small></span></a>`).join('');
  $('#case-summary').addEventListener('click',e=>{const link=e.target.closest('[data-track-link]');if(!link)return;track=link.dataset.trackLink;choice=0;renderMap();});
  function renderEvent(index) {
    const event = data.events[index];
    document.querySelectorAll('.hp-stop').forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
    $('#event-detail').setAttribute('aria-label',`${event.date}: ${event.title}`);
    $('#event-detail').innerHTML=[['What the record establishes',event.known],['What is still unknown',event.unknown],['How it could affect the case',event.effect]].map(([title,text],i)=>`<div><h3>${esc(title)}</h3><p>${esc(text)} ${i===0?refs(event.refs):''}</p></div>`).join('');
  }
  $('#timeline').innerHTML=data.events.map((e,i)=>`<button class="hp-stop" type="button" data-event="${i}" aria-pressed="false" aria-controls="event-detail"><time>${esc(e.date)}</time><i aria-hidden="true"></i><strong>${esc(e.title)}</strong></button>`).join('');
  $('#timeline').addEventListener('click',e=>{const b=e.target.closest('[data-event]');if(b)renderEvent(Number(b.dataset.event));});
  $('#ruling-flow').innerHTML=data.ruling.flow.map(r=>`<article><span>${esc(r.label)}</span><h3>${esc(r.title)}</h3>${paragraph(r)}</article>`).join('');
  $('#ruling-reasons').innerHTML=data.ruling.reasons.map(r=>`<article><h3>${esc(r.title)}</h3>${paragraph(r)}</article>`).join('');
  $('#witness-compare').innerHTML=data.witness.compare.map((w,i)=>`${i?'<div class="hp-not-equal" aria-hidden="true">≠</div>':''}<article><span>${esc(w.label)}</span><h3>${esc(w.title)}</h3>${paragraph(w)}</article>`).join('');
  $('#witness-hypotheses').innerHTML=`<div><h3>${esc(data.witness.hypothesisTitle)}</h3><p>${esc(data.witness.hypothesisNote)}</p></div><ul>${data.witness.hypotheses.map(h=>`<li>${esc(h.text)} ${refs(h.refs)}</li>`).join('')}</ul>`;
  $('#witness-question').innerHTML=esc(data.witness.question)+`<small>${esc(data.witness.limit)} ${refs(data.witness.refs)}</small>`;
  function renderCounsel(key) {
    const c=data.counsel[key];
    document.querySelectorAll('[data-counsel]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.counsel===key)));
    $('#counsel-detail').innerHTML=`<div class="hp-counsel-grid">${[[c.workTitle,c.work],[c.gapTitle,c.gaps]].map(([title,items])=>`<div><h3>${esc(title)}</h3>${items.map(i=>`<article class="hp-review-item">${i.kind?`<span class="hp-class">${esc(i.kind)}</span>`:''}<h4>${esc(i.title)}</h4>${paragraph(i)}</article>`).join('')}</div>`).join('')}</div><p class="hp-counsel-limit">${esc(c.limit)} ${refs(c.refs)}</p>`;
  }
  $('.hp-counsel-tabs').addEventListener('click',e=>{const b=e.target.closest('[data-counsel]');if(b)renderCounsel(b.dataset.counsel);});
  const tiles=items=>items.map(i=>`<article><h3>${esc(i.title)}</h3>${paragraph(i)}</article>`).join('');
  $('#next-answers').innerHTML=tiles(data.next);
  $('#dates').innerHTML=tiles(data.dates);
  $('#money-detail').innerHTML=data.money.map(m=>`<div><strong>${esc(m.value)}</strong><span>${esc(m.title)}</span>${paragraph(m)}</div>`).join('');
  const sourceLinks=s=>s.url?` <a href="${esc(s.url)}" target="_blank" rel="noopener">Read the official source</a>`:'';
  const sourceList=kind=>Object.entries(data.sources).filter(([,s])=>s.kind===kind).map(([id,s])=>`<div class="hp-source-row" id="source-${esc(id)}"><strong>${esc(id)}</strong><p><strong>${esc(s.title)}.</strong> ${esc(s.body)}${sourceLinks(s)}</p></div>`).join('');
  $('#case-sources').innerHTML=sourceList('case');$('#legal-sources').innerHTML=sourceList('law');
  $('#review-cutoff').textContent=data.cutoff;$('#scope').textContent=data.scope;
  const dialog=$('#source-dialog');let opener,priorOverflow='';
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-source]');if(!b)return;
    const s=data.sources[b.dataset.source];if(!s)return;
    opener=b;priorOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
    $('#source-label').textContent=`${b.dataset.source} · ${s.kind==='law'?'Official legal reference':'Dated case source'}`;
    $('#source-title').textContent=s.title;$('#source-body').innerHTML=`<p>${esc(s.body)}</p>${s.url?`<p>${sourceLinks(s)}</p>`:''}`;
    dialog.showModal();dialog.scrollTop=0;
  });
  $('#source-dialog button').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target!==dialog)return;const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();});
  dialog.addEventListener('close',()=>{document.body.style.overflow=priorOverflow;opener?.focus({preventScroll:true});});
  function revealHash(){const target=document.getElementById(location.hash.slice(1));const detail=target?.closest('details');if(detail){detail.open=true;requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}}
  window.addEventListener('hashchange',revealHash);
  renderMap();renderEvent(data.initialEvent ?? 0);renderCounsel('yours');revealHash();
  const navLinks=[...document.querySelectorAll('.hp-nav a')];
  const sections=navLinks.map(a=>document.getElementById(a.hash.slice(1)));
  function updateNav(){let current=sections[0];for(const section of sections)if(section.getBoundingClientRect().top<130)current=section;navLinks.forEach(a=>{if(a.hash==='#'+current.id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});}
  window.addEventListener('scroll',updateNav,{passive:true});updateNav();
})();
