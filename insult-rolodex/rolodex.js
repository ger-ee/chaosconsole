(() => {
  const $ = s => document.querySelector(s);
  const entries = QUOTES.map((quote,index) => ({quote,index,tags:getTags(quote)}));
  let filter='all', current=0, history=[], cursor=-1, toastTimer;
  const labels={all:'Anything goes',cats:'Cats',la:'Los Angeles',politics:'Politics',veep:'Veep',domestic:'Domestic chaos',existential:'Existential',general:'Wildcard'};
  const select=$('#rr-mood');
  FILTER_ORDER.forEach(key=>{const option=document.createElement('option');option.value=key;option.textContent=labels[key];select.append(option)});
  const pool=()=>entries.filter(e=>filter==='all'||e.tags.includes(filter));
  function show(index,animate=false){
    current=index;const entry=entries[index],card=$('#rr-card');
    $('#rr-quote').textContent=entry.quote;
    $('#rr-category').textContent=labels[filter==='all'?entry.tags[0]:filter];
    $('#rr-card-id').textContent=String(index+1).padStart(3,'0');
    card.dataset.length=entry.quote.length>210?'long':entry.quote.length>120?'medium':'short';
    $('#rr-prev').disabled=cursor<=0;
    if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches)card.animate([{transform:'rotate(-2deg) translateY(-8px)',opacity:.35},{transform:'rotate(.7deg)',opacity:1},{transform:'rotate(0)'}],{duration:330,easing:'cubic-bezier(.22,.7,.2,1)'});
  }
  function next(){const choices=pool().filter(e=>e.index!==current);const entry=choices[Math.floor(Math.random()*choices.length)]||pool()[0];history=history.slice(0,cursor+1);history.push(entry.index);cursor=history.length-1;show(entry.index,true)}
  function previous(){if(cursor>0){cursor--;show(history[cursor],true)}}
  function toast(message){$('#rr-toast').textContent=message;$('#rr-toast').dataset.visible='true';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#rr-toast').dataset.visible='false',2000)}
  async function copy(){try{await navigator.clipboard.writeText(entries[current].quote);toast('Copied. Use responsibly. Or don’t.')}catch{toast('Select the line to copy it.')}}
  select.addEventListener('change',()=>{filter=select.value;history=[];cursor=-1;next()});
  $('#rr-next').addEventListener('click',next);$('#rr-prev').addEventListener('click',previous);$('#rr-copy').addEventListener('click',copy);
  document.addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.altKey||event.target.closest('input,select,textarea,[contenteditable]')||document.querySelector('dialog[open]'))return;if(event.key==='ArrowRight'){event.preventDefault();next()}else if(event.key==='ArrowLeft'){event.preventDefault();previous()}else if(event.key.toLowerCase()==='c')copy()});
  current=Math.max(0,QUOTES.indexOf('Nothing more suspicious than a good mood.'));history=[current];cursor=0;show(current);
})();
