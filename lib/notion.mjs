import {createHash} from 'node:crypto';
export const normalize = id => String(id).replaceAll('-','').toLowerCase();
export const revision = b => createHash('sha256').update(JSON.stringify([b.last_edited_time,b.type,b[b.type],b.archived,b.in_trash])).digest('hex');
const supported = new Set(['paragraph','heading_1','heading_2','heading_3','bulleted_list_item','numbered_list_item','to_do','quote']);
export function editable(b) {
  const rt=b[b.type]?.rich_text;
  return !b.archived && !b.in_trash && supported.has(b.type) && Array.isArray(rt) && rt.every(t=>t.type==='text'&&!t.text.link&&!t.href&&Object.entries(t.annotations||{}).every(([k,v])=>k==='color'?v==='default':!v));
}
export function present(b,depth=0) {
  return {id:b.id,type:b.type,depth,revision:revision(b),editable:editable(b),checked:b[b.type]?.checked,text:(b[b.type]?.rich_text||[]).map(t=>t.plain_text??t.text?.content??'').join('')||b[b.type]?.title||'',hasChildren:b.has_children};
}
export function notionClient(token,transport=fetch) {
  let last=0;
  return async (path,method='GET',body)=>{
    await new Promise(r=>setTimeout(r,Math.max(0,350-(Date.now()-last)))); last=Date.now();
    const r=await transport('https://api.notion.com/v1/'+path,{method,headers:{Authorization:'Bearer '+token,'Notion-Version':'2026-03-11','Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
    if(!r.ok){const e=new Error(r.status===429?'Notion is busy. Wait a moment and retry.':r.status===401?'Your Notion session expired. Sign in again.':r.status===404?'Share this page with the ChaosConsole connection in Notion.':'Notion could not complete this request. Your draft is still here.');e.status=r.status===401?401:502;throw e;}
    return r.json();
  };
}
export async function blocks(api,id,depth=0,result=[]) {
  let cursor;
  do {
    const page=await api(`blocks/${id}/children?page_size=100`+(cursor?'&start_cursor='+encodeURIComponent(cursor):''));
    for(const b of page.results){
      if(result.length>=500)throw Object.assign(new Error('This page is too large for this first editor. Open it in Notion.'),{status:422});
      result.push(present(b,depth));
      if(b.has_children && !['child_page','child_database','synced_block'].includes(b.type)){
        if(depth>=12)throw Object.assign(new Error('This page has deeply nested content. Open it in Notion.'),{status:422});
        await blocks(api,b.id,depth+1,result);
      }
    }
    cursor=page.has_more?page.next_cursor:null;
  }while(cursor);
  return result;
}
export async function belongs(api,block,page){
  let current=block;
  for(let n=0;n<15;n++){
    const p=current.parent;
    if(p?.type==='page_id')return normalize(p.page_id)===normalize(page);
    if(p?.type!=='block_id')return false;
    current=await api('blocks/'+p.block_id);
  }
  return false;
}
export async function save(api,page,changes){
  if(!Array.isArray(changes)||!changes.length||changes.length>30)throw Object.assign(new Error('Save between 1 and 30 edited blocks at a time.'),{status:400});
  const seen=new Set(),ready=[];
  for(const c of changes){
    if(!/^[a-f0-9-]{32,36}$/i.test(c.id)||typeof c.text!=='string'||c.text.length>20000||seen.has(c.id)||!/^([a-f0-9]{64})$/.test(c.revision))throw Object.assign(new Error('Invalid edit.'),{status:400});
    seen.add(c.id);
    const b=await api('blocks/'+c.id);
    if(!await belongs(api,b,page)||!editable(b))throw Object.assign(new Error('This block cannot be edited here.'),{status:403});
    if(revision(b)!==c.revision)throw Object.assign(new Error('This page changed in Notion. Copy your draft before reloading to compare the changes.'),{status:409});
    if(b.type==='to_do'&&typeof c.checked!=='boolean')throw Object.assign(new Error('Invalid checkbox.'),{status:400});
    ready.push([b,c]);
  }
  const saved=[];
  try{
    for(const [b,c] of ready){
      const latest=await api('blocks/'+b.id);
      if(revision(latest)!==c.revision)throw Object.assign(new Error('Content changed during saving. Copy your remaining draft before reloading.'),{status:409});
      const rich_text=[];for(let i=0;i<c.text.length;i+=2000)rich_text.push({type:'text',text:{content:c.text.slice(i,i+2000)}});
      const body={[b.type]:{rich_text,...(b.type==='to_do'?{checked:c.checked}:{})}};
      const updated=await api('blocks/'+b.id,'PATCH',body);
      saved.push(present(updated));
    }
    return {saved};
  }catch(e){e.saved=saved;throw e;}
}
