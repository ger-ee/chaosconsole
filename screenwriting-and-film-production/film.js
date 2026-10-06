(() => {
  const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
  const lessons=$$('.fs-lesson'),index=new Map(lessons.map(e=>[e.dataset.id,e]));
  const home=$('#fs-home'),reader=$('#fs-reader'),outline=$('#fs-outline'),search=$('#fs-search');
  let current=null;
  lessons.forEach(lesson=>{const heading=lesson.querySelector('h3');heading.setAttribute('role','heading');heading.setAttribute('aria-level','1')});
  function bookmark(id){try{localStorage.setItem('cc-film-last-lesson',id)}catch{}}
  function resume(){let id;try{id=localStorage.getItem('cc-film-last-lesson')}catch{}const el=index.get(id);if(el){const link=$('#fs-resume');link.hidden=false;link.href='#'+id;link.textContent='Continue: '+el.dataset.title}}
  function render(){
    let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{id='contents'}
    const lesson=index.get(id);
    lessons.forEach(e=>e.hidden=e!==lesson);
    home.hidden=!!lesson;reader.hidden=!lesson;
    outline.dataset.open='false';$('#fs-show-outline').setAttribute('aria-expanded','false');
    if(!lesson){current=null;document.title='Film School — Chaos Console';resume();if(/^phase-\d$/.test(id)){const chapter=document.getElementById(id);if(chapter){chapter.open=true;requestAnimationFrame(()=>chapter.scrollIntoView({block:'start',behavior:'instant'}))}}else scrollTo({top:0,behavior:'instant'});return}
    current=id;bookmark(id);document.title=lesson.dataset.title+' — Film School';
    $('#fs-reader-phase').textContent=lesson.dataset.phaseTitle;
    outline.replaceChildren();const heading=document.createElement('p');heading.textContent=lesson.dataset.phaseTitle;outline.append(heading);
    lessons.filter(e=>e.dataset.phase===lesson.dataset.phase).forEach(e=>{const a=document.createElement('a');a.href='#'+e.dataset.id;a.textContent=e.dataset.title;if(e===lesson)a.setAttribute('aria-current','page');outline.append(a)});
    const n=lessons.indexOf(lesson);
    [['#fs-previous',lessons[n-1],'Previous'],['#fs-next',lessons[n+1],'Next']].forEach(([sel,target,label])=>{const link=$(sel);link.href=target?'#'+target.dataset.id:'#contents';link.querySelector('small').textContent=target?label:'The curriculum';link.querySelector('span').textContent=target?target.dataset.title:'Back to all lessons'});
    scrollTo({top:0,behavior:'instant'});
  }
  search.addEventListener('input',()=>{const q=search.value.trim().toLowerCase();let count=0;$$('.fs-chapter').forEach(chapter=>{let visible=0;chapter.querySelectorAll('[data-lesson]').forEach(a=>{const lesson=index.get(a.dataset.lesson),match=!q||lesson.textContent.toLowerCase().includes(q);a.hidden=!match;if(match){visible++;count++}});chapter.hidden=!visible;chapter.open=!!q&&visible>0});const status=$('#fs-search-status');status.hidden=!q;status.textContent=count?count+' matching '+(count===1?'lesson':'lessons'):'No matching lessons. Try “dialogue”, “lighting”, or a film title.'});
  $('#fs-show-outline').addEventListener('click',()=>{const open=outline.dataset.open!=='true';outline.dataset.open=String(open);$('#fs-show-outline').setAttribute('aria-expanded',String(open))});
  document.addEventListener('click',event=>{const a=event.target.closest('a[href^="#"]');if(a&&a.hash===location.hash&&(index.has(a.hash.slice(1))||a.hash==='#contents')){event.preventDefault();render()}});
  addEventListener('hashchange',render);resume();render();
})();
