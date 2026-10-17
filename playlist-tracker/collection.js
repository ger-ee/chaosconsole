let data=loadData();
(() => {
  'use strict';
  const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
  const names=()=>Object.keys(data.playlists),last=()=>data.months.length-1;
  const number=n=>Number(n).toLocaleString('en-US'),signed=n=>(n>0?'+':'')+number(n);
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // Current Spotify artwork. Source IDs and image hashes: covers/spotify/manifest.json.
  const coverFiles={"Monday's Mixtape":"mondays-mixtape-9eb942beec2c.jpg","Groove":"groove-6232257e6d6f.jpg","Guide to Indie":"guide-to-indie-e15bdbb083a7.jpg","Ancora":"ancora-8561b36a481c.jpg","Potpourri":"potpourri-2735f7b055be.jpg","Cloudbuster":"cloudbuster-b8b1d410b66d.jpg","Broken":"broken-b74f9e0cfda6.jpg","run":"run-6b615484f4eb.jpg","Oddities":"oddities-2f5461b0aaf2.jpg","Orpheus":"orpheus-5f274b4bb124.jpg","Afterglow":"afterglow-94890a649970.jpg","Thirst":"thirst-25eb4cd0e9db.jpg","Vertigo":"vertigo-03cca8e100e2.jpg","Masterpiece":"masterpiece-867e861f7ac3.jpg","Broadway":"broadway-35d4c6c972db.jpg"};
  const cover=name=>coverFiles[name]?'/playlist-tracker/covers/spotify/'+coverFiles[name]:'';
  const spotify=name=>SPOTIFY_URLS[name]||SPOTIFY_PROFILE;
  let chartMode='years',gainRange=12;
  let featured=0,range=12,seriesName='all',historyChart,detailChart,detailName,toastTimer;
  function art(host,name,lazy=false){
    host.classList.add('pl-art');host.replaceChildren();
    const fallback=document.createElement('div');fallback.className='pl-fallback';fallback.innerHTML='<strong>'+esc(name)+'</strong><span></span>';host.append(fallback);
    if(cover(name)){const img=new Image();img.alt=name+' cover';img.loading=lazy?'lazy':'eager';img.decoding='async';img.addEventListener('load',()=>img.dataset.ready='true');img.addEventListener('error',()=>{img.dataset.failed='true';fallback.querySelector('span').textContent='Cover unavailable'});img.src=cover(name);host.append(img)}
  }
  function showFeatured(index,animate=false){
    const all=names();featured=(index+all.length)%all.length;const name=all[featured];
    $('#pl-feature-title').textContent=name;
    $('#pl-feature-note').textContent='followers in the '+data.months[last()]+' snapshot';
    const counts=data.playlists[name],yearIndex=data.months.findIndex(m=>monthLabelToValue(m)===monthLabelToValue(data.months[last()])-12);
    $('#pl-feature-metrics').innerHTML='<strong>'+number(counts[last()])+'</strong><div>'+(yearIndex>=0?'<span>'+signed(counts[last()]-counts[yearIndex])+' vs '+esc(data.months[yearIndex])+'</span>':'')+'<span>'+signed(counts[last()]-counts[0])+' since '+esc(data.months[0])+'</span></div>';
    $('.pl-feature-context').textContent='Featured · '+String(featured+1).padStart(2,'0')+' / '+all.length;
    renderStrip();
    $('#pl-feature-position').textContent=String(featured+1).padStart(2,'0')+' / '+all.length;
    $('#pl-feature-listen').href=spotify(name);art($('#pl-feature-art'),name);
    if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches)$('#pl-feature-art').animate([{transform:'translateX(12px)',opacity:.35},{transform:'translateX(0)',opacity:1}],{duration:260,easing:'ease-out'});
  }
  function drawCatalog(){
    const query=$('#pl-search').value.trim().toLowerCase(),sort=$('#pl-sort').value;
    let visible=names().filter(name=>name.toLowerCase().includes(query));
    if(sort==='followers')visible.sort((a,b)=>data.playlists[b][last()]-data.playlists[a][last()]);
    if(sort==='name')visible.sort((a,b)=>a.localeCompare(b));
    const grid=$('#pl-grid');grid.replaceChildren();
    visible.forEach(name=>{const item=document.createElement('article');item.className='pl-record';
      const button=document.createElement('button');button.type='button';button.className='pl-record-cover';button.setAttribute('aria-label','View '+name);art(button,name,true);button.addEventListener('click',()=>openDetail(name));
      const caption=document.createElement('div');caption.className='pl-record-caption';caption.innerHTML='<div><h3>'+esc(name)+'</h3><p>'+number(data.playlists[name][last()])+' followers</p></div><a href="'+esc(spotify(name))+'" target="_blank" rel="noopener" aria-label="Listen to '+esc(name)+' on Spotify">↗</a>';
      item.append(button,caption);grid.append(item);
    });
    $('#pl-empty').hidden=visible.length!==0;
    $('#pl-collection-caption').textContent=names().length+' playlists. Collected by Gary.';
  }
  function values(name){return name==='all'?data.months.map((_,i)=>names().reduce((sum,n)=>sum+data.playlists[n][i],0)):data.playlists[name]}
  function chart(canvas,labels,counts,compact=false){return new Chart(canvas,{type:'line',data:{labels,datasets:[{label:'Followers',data:counts,borderColor:'#edbc42',backgroundColor:'transparent',borderWidth:compact?2:2.5,fill:false,tension:.15,pointRadius:compact?1:2.5,pointHoverRadius:5,pointBackgroundColor:'#edbc42',pointBorderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{backgroundColor:'#202020',titleColor:'#fff1dd',bodyColor:'#fff1dd',padding:12,displayColors:false,callbacks:{label:item=>number(item.parsed.y)+' followers'}}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#aaa39a',font:{family:'IBM Plex Sans',size:compact?9:11},maxRotation:0,maxTicksLimit:compact?4:8}},y:{beginAtZero:true,border:{display:false},grid:{color:'#ffffff12'},ticks:{color:'#aaa39a',font:{family:'IBM Plex Sans',size:compact?9:11},maxTicksLimit:5,precision:0}}}}})}
  function renderHistory(){
    const counts=values(seriesName),current=counts[last()],yearIndex=data.months.findIndex(m=>monthLabelToValue(m)===monthLabelToValue(data.months[last()])-12),delta=yearIndex>=0?current-counts[yearIndex]:0,first=counts[0],start=range==='all'?0:Math.max(0,data.months.length-range);
    $('#pl-history-caption').textContent=data.months.length+' recorded snapshots. Source counts checked '+SNAPSHOT_UPDATED_AT+'.';
    $('#pl-history-numbers').innerHTML=[['Followers',number(current)],[yearIndex>=0?'Since '+data.months[yearIndex]:'No year-earlier snapshot',yearIndex>=0?signed(delta):'—'],['Since '+data.months[0],signed(current-first)]].map(([label,value])=>'<div><strong>'+value+'</strong><span>'+esc(label)+'</span></div>').join('');
    historyChart?.destroy();historyChart=chart($('#pl-history-chart'),data.months.slice(start),counts.slice(start));if(chartMode==='years')compareYears(counts);renderGainers();
    const rows=seriesName==='all'?names():[seriesName];
    $('#pl-table').innerHTML='<caption class="room-sr">Recorded follower counts for all available snapshots</caption><thead><tr><th scope="col">Playlist</th>'+data.months.map(m=>'<th scope="col">'+esc(m)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(name=>'<tr><th scope="row">'+esc(name)+'</th>'+data.playlists[name].map(n=>'<td>'+number(n)+'</td>').join('')+'</tr>').join('')+'</tbody>';
  }
  function switchView(view,focus=false){
    $('#pl-collection').hidden=false;$('#pl-history').hidden=false;
    $$('.pl-tabs button').forEach(button=>{const active=button.dataset.view===view;button.setAttribute('aria-pressed',String(active));button.tabIndex=0;if(focus&&active)button.focus()});
    if(view==='history')renderHistory();document.getElementById(view==='history'?'pl-history':'pl-collection').scrollIntoView({behavior:'instant',block:'start'});
    const url=new URL(location.href);if(view==='history')url.hash='history';else url.hash='';history.replaceState(null,'',url);
  }
  function openHistory(name){seriesName=name;$('#pl-series').value=name;switchView('history')}
  function openDialog(dialog){dialog.showModal();document.body.style.overflow='hidden'}
  $$('.room-dialog').forEach(dialog=>{dialog.addEventListener('close',()=>{document.body.style.overflow=''});dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close()})});
  $$('[data-close]').forEach(button=>button.addEventListener('click',()=>document.getElementById(button.dataset.close).close()));
  function openDetail(name){
    detailName=name;const counts=data.playlists[name],current=counts[last()],delta=current-(counts[last()-1]??current);
    $('#pl-detail-title').textContent=name;$('#pl-detail-note').textContent='Recorded through '+data.months[last()]+'.';
    $('#pl-detail-numbers').innerHTML='<div><strong>'+number(current)+'</strong><span>Followers</span></div><div><strong>'+signed(delta)+'</strong><span>Since '+esc(data.months[last()-1]||data.months[0])+'</span></div>';
    $('#pl-detail-listen').href=spotify(name);art($('#pl-detail-art'),name);
    openDialog($('#pl-detail'));detailChart?.destroy();detailChart=chart($('#pl-detail-chart'),data.months,counts,true);
  }
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function inputMonth(label){const [m,y]=label.split(' ');return (Number(y)<100?2000+Number(y):Number(y))+'-'+String(months.indexOf(m)+1).padStart(2,'0')}
  function monthFromInput(value){const [y,m]=value.split('-');return months[Number(m)-1]+' '+y.slice(-2)}
  function entryFields(){
    if(!$('#pl-month').value)return;const label=monthFromInput($('#pl-month').value),idx=data.months.indexOf(label),monthValue=monthLabelToValue(label),prior=data.months.filter(m=>monthLabelToValue(m)<monthValue).at(-1),priorIndex=data.months.indexOf(prior);
    $('#pl-entry-meta').textContent=idx>=0?'Editing the saved '+label+' snapshot.':'New snapshot for '+label+'.';
    $('#pl-save').textContent=idx>=0?'Update snapshot':'Save snapshot';
    $('#pl-entry-fields').innerHTML=names().map((name,i)=>'<div class="pl-entry-row"><label for="pl-count-'+i+'">'+esc(name)+'</label><input id="pl-count-'+i+'" name="count-'+i+'" type="number" min="0" step="1" required value="'+(data.playlists[name][idx>=0?idx:priorIndex]??0)+'" data-name="'+esc(name)+'"></div>').join('');
  }
  function openEntry(){const next=monthLabelToValue(data.months[last()])+1;$('#pl-month').value=Math.floor(next/12)+'-'+String(next%12+1).padStart(2,'0');$('#pl-entry-error').hidden=true;entryFields();openDialog($('#pl-entry'))}
  $('#pl-entry-form').addEventListener('submit',event=>{
    event.preventDefault();if(!event.currentTarget.reportValidity())return;
    const label=monthFromInput($('#pl-month').value),value=monthLabelToValue(label),next=JSON.parse(JSON.stringify(data));let idx=next.months.indexOf(label);
    if(idx<0){idx=next.months.findIndex(m=>monthLabelToValue(m)>value);if(idx<0)idx=next.months.length;next.months.splice(idx,0,label);names().forEach(n=>next.playlists[n].splice(idx,0,idx?next.playlists[n][idx-1]:0))}
    $$('#pl-entry-fields input').forEach(input=>next.playlists[input.dataset.name][idx]=Number(input.value));
    try{localStorage.setItem(STORAGE_KEY,JSON.stringify(next));data=next;$('#pl-entry').close();showFeatured(featured);drawCatalog();renderHistory();toast('Snapshot saved for '+label)}catch{$('#pl-entry-error').hidden=false;$('#pl-entry-error').textContent='This browser could not save the snapshot. Free some storage, then try again.'}
  });
  function toast(message){$('#pl-toast').textContent=message;$('#pl-toast').dataset.visible='true';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#pl-toast').dataset.visible='false',2300)}
  function exportCSV(){const quote=s=>'"'+String(s).replaceAll('"','""')+'"';const csv=['Playlist,'+data.months.map(quote).join(','),...names().map(n=>quote(n)+','+data.playlists[n].join(','))].join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='playlist-history.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  names().forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;$('#pl-series').append(option)});
  $$('.pl-tabs button').forEach(button=>{button.addEventListener('click',()=>switchView(button.dataset.view));button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const view=event.key==='Home'?'collection':event.key==='End'?'history':button.dataset.view==='collection'?'history':'collection';switchView(view,true)})});
  $('#pl-feature-prev').addEventListener('click',()=>showFeatured(featured-1,true));$('#pl-feature-next').addEventListener('click',()=>showFeatured(featured+1,true));$('#pl-feature-history').addEventListener('click',()=>openHistory(names()[featured]));
  $('#pl-search').addEventListener('input',drawCatalog);$('#pl-sort').addEventListener('change',drawCatalog);
  $('#pl-series').addEventListener('change',e=>{seriesName=e.target.value;renderHistory()});
  $$('#pl-range button').forEach(button=>button.addEventListener('click',()=>{range=button.dataset.range==='all'?'all':Number(button.dataset.range);$$('#pl-range button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));renderHistory()}));
  $('#pl-detail-history').addEventListener('click',()=>{$('#pl-detail').close();openHistory(detailName)});
  $('#pl-add').addEventListener('click',openEntry);$('#pl-month').addEventListener('change',entryFields);$('#pl-export').addEventListener('click',exportCSV);

  function renderStrip(){
    const host=$('#pl-strip');host.replaceChildren();names().forEach((name,i)=>{const b=document.createElement('button');b.type='button';b.setAttribute('aria-pressed',String(i===featured));b.innerHTML='<small>'+String(i+1).padStart(2,'0')+'</small><span>'+esc(name)+'</span><b>'+number(data.playlists[name][last()])+'</b>';b.addEventListener('click',()=>showFeatured(i,true));host.append(b)});
  }
  function compareYears(counts){
    const years=[...new Set(data.months.map(m=>Math.floor(monthLabelToValue(m)/12)))].sort((a,b)=>b-a),colors=['#edbc42','#eee7db','#716b62'];
    historyChart.data.labels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    historyChart.data.datasets=years.map((year,j)=>({label:String(year),data:Array.from({length:12},(_,month)=>{const i=data.months.findIndex(m=>monthLabelToValue(m)===year*12+month);return i<0?null:counts[i]}),borderColor:colors[j%3],borderWidth:j===0?2.5:1.5,pointRadius:j===0?3:0,pointBackgroundColor:'#121212',pointBorderColor:colors[j%3],pointBorderWidth:2,spanGaps:false,tension:0}));
    historyChart.options.plugins.legend={display:true,position:'top',align:'end',labels:{color:'#eee7db',boxWidth:14,boxHeight:2,font:{size:11}}};historyChart.update();
  }
  function renderGainers(){
    const target=monthLabelToValue(data.months[last()])-gainRange,idx=data.months.findIndex(m=>monthLabelToValue(m)===target),host=$('#pl-gain-grid');host.replaceChildren();
    $('#pl-gain-note').textContent=idx<0?'No snapshot recorded for the comparison month.':('Compared with '+data.months[idx]+'.');if(idx<0)return;
    const ranked=names().map(name=>({name,from:data.playlists[name][idx],to:data.playlists[name][last()]})).map(p=>({...p,delta:p.to-p.from})).sort((a,b)=>b.delta-a.delta).filter(p=>p.delta>0).slice(0,5);
    if(!ranked.length){$('#pl-gain-note').textContent='No gains since '+data.months[idx]+'.';return}
    ranked.forEach(p=>{const b=document.createElement('button');b.type='button';b.className='pl-gain-card';const image=document.createElement('div');art(image,p.name);const text=document.createElement('div');text.innerHTML='<strong>'+signed(p.delta)+'</strong><b>'+esc(p.name)+'</b><small>'+number(p.from)+' → '+number(p.to)+'</small>';b.append(image,text);b.addEventListener('click',()=>openDetail(p.name));host.append(b)});
  }
  $$('[data-mode]').forEach(b=>b.addEventListener('click',()=>{chartMode=b.dataset.mode;$$('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('#pl-range').hidden=chartMode==='years';renderHistory()}));
  $$('[data-gain]').forEach(b=>b.addEventListener('click',()=>{gainRange=Number(b.dataset.gain);$$('[data-gain]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));renderGainers()}));
  $('#pl-range').hidden=true;

  showFeatured(0);drawCatalog();renderHistory();if(location.hash==='#history')switchView('history');
})();
