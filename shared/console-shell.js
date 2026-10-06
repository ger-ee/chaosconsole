/* Threshold room architecture. Source content and room tools stay in their own pages. */
(function () {
  'use strict';
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>Array.from(r.querySelectorAll(s));
  const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const path=location.pathname.replace(/\/index\.html$/,'/');
  const routes=window.ThresholdRoutes||[];
  const route=routes.find(r=>r.path===path);
  if(!route)return;
  document.documentElement.dataset.threshold=route.key;
  document.documentElement.dataset.roomKind=route.kind;
  document.documentElement.dataset.roomGroup=route.group.toLowerCase();
  const groups={Studio:['rundown','binder','almanac','atlas','playlists'],Life:['hearing','possession','ledger','wellness'],Reference:['film','archive-map','color','ai','ecosystem','rolodex']};
  let activeGroup=route.group,opener=null,priorOverflow='';
  function brief(node,label){if(!node||node.closest('.th-source-brief'))return;const d=document.createElement('details');d.className='th-source-brief';const s=document.createElement('summary');s.textContent=label;node.before(d);d.append(s,node);return d}
  function hide(selector){$$(selector).forEach(e=>e.classList.add('th-retired-chrome'))}
  function titleHide(selector){$$(selector).forEach(e=>e.classList.add('th-original-title'))}
  function mount(){
    if($('.th-entrance'))return;
    const entrance=document.createElement('header');entrance.className='th-entrance';entrance.id='th-page-top';
    const parent=route.parent?`<a href="${route.parent}">${esc(route.parentTitle)}</a>`:`<span>${esc(route.group)}</span>`;
    entrance.innerHTML=`<img class="th-architecture" src="/shared/threshold/architecture.png" alt="" fetchpriority="high"><nav class="th-topbar" aria-label="Chaos Console"><a class="th-brand" href="/"><span class="th-mark" aria-hidden="true"></span>Chaos Console</a><div class="th-context">${parent}<span>/</span><span>${esc(route.title)}</span></div><button class="th-room-switch" aria-haspopup="dialog" aria-controls="th-room-drawer">Rooms <svg viewBox="0 0 18 18" aria-hidden="true"><path d="M9 2v14M2 9h14"/></svg></button></nav><div class="th-title-wrap"><div class="th-heading"><p class="th-section-label">${route.parent?esc(route.parentTitle):esc(route.group)}</p><h1 ${route.title.length>19?'class="th-long"':''}>${esc(route.title)}<span>.</span></h1></div><p class="th-purpose">${esc(route.purpose)}</p></div>`;
    const skip=document.createElement('a');skip.className='th-skip';skip.href='#th-room-content';skip.textContent='Skip to content';
    document.body.prepend(entrance);document.body.prepend(skip);
    const main=$('main:not(.th-drawer-main),.app,.shell,.container,.wrap,#dc-root');if(main){if(!main.id)main.id='th-room-content';else skip.href='#'+main.id}
    if(route.date){const date=document.createElement('p');date.className='th-source-date';date.textContent='Source snapshot · '+route.date;entrance.after(date)}
    const drawer=document.createElement('dialog');drawer.id='th-room-drawer';drawer.className='th-drawer';drawer.setAttribute('aria-labelledby','th-drawer-title');
    drawer.innerHTML=`<div class="th-drawer-top"><p>Chaos Console</p><button class="th-close" aria-label="Close room navigator">×</button></div><div class="th-drawer-main"><div class="th-drawer-side"><h2 class="th-drawer-title" id="th-drawer-title">Make<br>room.</h2><p>A different space for each part of your world.</p><nav class="th-group-tabs" aria-label="Room groups">${Object.keys(groups).map(g=>`<button data-th-group="${g}" aria-pressed="${g===activeGroup}">${g}</button>`).join('')}</nav></div><div><input class="th-find" type="search" aria-label="Find a room" placeholder="Find a room…"><div class="th-room-list"></div></div></div>`;
    document.body.append(drawer);
    function renderRooms(){const q=$('.th-find',drawer).value.trim().toLowerCase();const list=(q?Object.values(groups).flat():groups[activeGroup]).map(k=>routes.find(r=>r.key===k)).filter(r=>r&&(!q||[r.title,r.purpose,r.group].join(' ').toLowerCase().includes(q)));$('.th-room-list',drawer).innerHTML=list.length?list.map(r=>`<a href="${r.path}" ${r.path===path?'aria-current="page"':''}><span>${esc(r.title)}<small>${esc(r.purpose)}</small></span><span aria-hidden="true">↗</span></a>`).join(''):'<p class="th-empty">No rooms match that search.</p>'}
    function openRooms(event){opener=event?.currentTarget||document.activeElement;priorOverflow=document.body.style.overflow;document.body.style.overflow='hidden';drawer.showModal();renderRooms();$('.th-find',drawer).focus()}
    $('.th-room-switch',entrance).addEventListener('click',openRooms);$('.th-close',drawer).addEventListener('click',()=>drawer.close());drawer.addEventListener('close',()=>{document.body.style.overflow=priorOverflow;opener?.focus({preventScroll:true})});$('.th-find',drawer).addEventListener('input',renderRooms);
    $$('[data-th-group]',drawer).forEach(b=>b.addEventListener('click',()=>{activeGroup=b.dataset.thGroup;$('.th-find',drawer).value='';$$('[data-th-group]',drawer).forEach(x=>x.setAttribute('aria-pressed',x===b));renderRooms()}));
    document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!drawer.open)openRooms();else drawer.close()}});
    adapt();
    if(route.kind!=='map'){const footer=document.createElement('footer');footer.className='th-footer';footer.innerHTML=`<span class="th-mark" aria-hidden="true"></span><span>${esc(route.title)} / Chaos Console</span><a href="#th-page-top">Back to top ↑</a>`;document.body.append(footer)}
    document.dispatchEvent(new CustomEvent('threshold:ready',{detail:route}));
    // Use the same public status manifest as the landing page; no separate freshness clock.
    if(route.date&&!route.parent)fetch('/data/console-status.json').then(r=>r.ok?r.json():null).then(data=>{const record=data?.rooms?.find(r=>r.href===route.path);if(record?.updated&&$('.th-source-date'))$('.th-source-date').textContent='Source snapshot · '+new Date(record.updated+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}).catch(()=>{});
  }
  function adapt(){
    hide('.topnav,.theme-toggle,.theme-switch,.theme-btn,.noise,.bg-ambience,.bg-grid');
    if(route.kind==='casework'){
      titleHide('.hero h1');hide('.hero-top');const hero=$('.hero');if(hero){const nav=$('.nav-in',hero);if(nav)hero.before(nav);brief($('.hero-sub',hero),'Read the source brief · '+route.date)}
      $$('.board .tile-d').forEach(node=>{const d=document.createElement('details');d.className='th-detail';d.innerHTML='<summary>Read the record</summary>';node.before(d);d.append(node)});
      const notice=$('.notice');if(notice)brief(notice,'About this record');
    }
    if(route.key==='playlists'){
      const actions=$('.chrome-actions');if(actions){const bar=document.createElement('div');bar.className='th-room-toolbar';$('.th-source-date')?.after(bar);bar.append(actions)}hide('.chrome');titleHide('.hero-title');hide('.hero-status,.hero-panel>.eyebrow');
      const stories=$('#storyGrid');if(stories)brief(stories,'Portfolio observations');
      [['#catalog-title','catalog'],['#portfolio-pulse-title','portfolio'],['#leaderboard-title','leaderboard-section']].forEach(([sel,id])=>{const h=$(sel);if(h)h.closest('section').id=id});
    }
    if(route.key==='wellness'){
      titleHide('.hero h1');hide('.hero-card>.eyebrow');brief($('.hero .lede'),'About the readings');
    }
    if(route.key==='atlas'){hide('.crumbs,.theme-btn');titleHide('.masthead .brand');const strip=$('.strip');if(strip)strip.classList.add('th-atlas-toolbar')}
    if(route.kind==='deck'){
      hide('.site-head,.intro-panel>.eyebrow');titleHide('.intro-panel>h1');const intro=$('.intro-copy');if(intro)brief(intro,'About this collection');
      const helper=$('.helper-line');if(helper&&route.key==='reading-deck')helper.textContent='Keyboard: → next, ← previous, C copy.';
    }
    if(['manual','chapter'].includes(route.kind)){
      const nav=$('.site-header .top-links');if(nav){const bar=document.createElement('div');bar.className='th-room-toolbar th-manual-nav';($('.th-source-date')||$('.th-entrance')).after(bar);bar.append(nav)}hide('.site-header');titleHide('.content>.hero h1');hide('.content>.hero>.breadcrumb');
      const subtitle=$('.content>.hero>.subtitle');if(subtitle){if(route.kind==='chapter')subtitle.classList.add('th-retired-chrome');else brief(subtitle,'About the Almanac')}
    }
    if(route.key==='binder'){
      hide('.nav-top .back-link,.nav-top .title-mini,.hero-panel,.hero-eyebrow,.filter-note');titleHide('.hero h1');brief($('.hero-sub'),'About the Binder');
      $('.sticky')?.classList.add('th-binder-nav');
    }
    if(route.key==='film'){hide('.back-nav');titleHide('.title-section');const toggle=$('.menu-toggle');if(toggle){toggle.setAttribute('aria-label','Open chapter contents');toggle.setAttribute('aria-expanded','false');toggle.addEventListener('click',()=>toggle.setAttribute('aria-expanded',$('.sidebar')?.classList.contains('open')?'true':'false'))}}
    if(route.key==='ecosystem'){
      hide('.container>.header>h1,.container>.header>.version-badge');$$('body>div').forEach(e=>{if(e.children.length===1&&e.firstElementChild?.matches('a[href="../index.html"]'))e.classList.add('th-retired-chrome')});brief($('.container>.header>.subtitle'),'About this maintenance record');
    }
    if(route.key==='color'){
      hide('.container>.topnav-back');titleHide('.header h1');const note=$('.header .meta');if(note)brief(note,'Document version and source lineage');
      const bar=document.createElement('div');bar.className='th-color-ribbon';bar.setAttribute('aria-label','The five canonical colors');const colors=[['#DC2626','Hot'],['#D97706','In flight'],['#16A34A','Done'],['#0077BC','Waiting'],['#009866','Reference']];bar.innerHTML=colors.map(([c,t])=>`<a href="#five-colors" style="--swatch:${c}"><i></i><span>${t}</span></a>`).join('');$('.container>.header')?.after(bar);
    }
    if(route.key==='archive-map'){titleHide('.masthead h1');hide('.masthead>.kicker');brief($('.masthead>.sub'),'About this source map')}
    if(route.key==='money-archive')titleHide('.container>.header h1');
    if(route.key==='wellness-widgets')titleHide('body>header:not(.th-entrance) h1');
    if(route.key==='ledger'&&window.ThresholdLedger)window.ThresholdLedger();
    if(route.kind==='map'){
      const tuneMap=()=>{$$('#dc-root header button').filter(b=>/^(DARK|LIGHT)$/.test(b.textContent.trim())).forEach(b=>b.parentElement.classList.add('th-retired-chrome'));const track=$('#track');if(track){track.previousElementSibling?.classList.add('th-map-phases');track.nextElementSibling?.classList.add('th-cut-tray')}};
      tuneMap();const host=$('#dc-root');if(host){const observer=new MutationObserver(tuneMap);observer.observe(host,{childList:true,subtree:true})}
    }
    // Tables keep horizontal scrolling within the room rather than widening the page.
    $$('table').forEach(t=>{if(t.closest('.th-table-scroll'))return;if(t.closest('.table-wrap,.table-scroll,.heatmap-wrap')){t.parentElement.classList.add('th-table-scroll');return;}const w=document.createElement('div');w.className='th-table-scroll';t.before(w);w.append(t)});
  }
  function chartTheme(){
    if(!window.Chart)return;
    const styles=getComputedStyle(document.documentElement),ink=styles.getPropertyValue('--th-ink').trim(),muted=styles.getPropertyValue('--th-secondary').trim(),line=styles.getPropertyValue('--th-line').trim(),paper=styles.getPropertyValue('--th-paper').trim();
    const apply=chart=>{const o=chart.options;if(o.scales)Object.values(o.scales).forEach(s=>{if(s.ticks){s.ticks.color=muted;s.ticks.font={...s.ticks.font,family:'Threshold Sans',size:11}}if(s.grid)s.grid.color=line;if(s.title){s.title.color=muted;s.title.font={...s.title.font,family:'Threshold Sans'}}});if(o.plugins?.legend?.labels){o.plugins.legend.labels.color=ink;o.plugins.legend.labels.font={...o.plugins.legend.labels.font,family:'Threshold Sans'}}if(o.plugins?.tooltip){Object.assign(o.plugins.tooltip,{backgroundColor:ink,titleColor:paper,bodyColor:paper,borderColor:line,borderWidth:1});o.plugins.tooltip.titleFont={family:'Threshold Sans'};o.plugins.tooltip.bodyFont={family:'Threshold Sans'}}};
    Chart.defaults.font.family='Threshold Sans';Chart.defaults.color=muted;Chart.register({id:'thresholdPalette',beforeUpdate:apply});Object.values(Chart.instances||{}).forEach(c=>{apply(c);c.update('none')});
  }
  function ready(){requestAnimationFrame(()=>{mount();chartTheme()})}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();
})();
