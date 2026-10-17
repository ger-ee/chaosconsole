import {randomBytes} from 'node:crypto';
import {seal,unseal,cookies,cookie} from '../lib/session.mjs';
import {notionClient,blocks,save,normalize} from '../lib/notion.mjs';
export default async function handler(req,res){
  res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','application/json');
  const send=(status,data)=>{res.statusCode=status;res.end(JSON.stringify(data));};
  const redirect=url=>{res.statusCode=302;res.setHeader('Location',url);res.end();};
  const env=process.env;
  const consoleOrigin='https://chaosconsole.com';
  const requestOrigin=req.headers.origin;
  if(requestOrigin===consoleOrigin){res.setHeader('Access-Control-Allow-Origin',consoleOrigin);res.setHeader('Vary','Origin');res.setHeader('Access-Control-Allow-Headers','Authorization, Content-Type');res.setHeader('Access-Control-Allow-Methods','GET, POST, OPTIONS');}
  if(req.method==='OPTIONS')return send(requestOrigin===consoleOrigin?204:403,{});
  const configured=['APP_ORIGIN','NOTION_CLIENT_ID','NOTION_CLIENT_SECRET','ALLOWED_USER_ID','PAGE_IDS'].every(k=>env[k])&&/^[a-f0-9]{64}$/i.test(env.SESSION_KEY||'');
  try{
    const url=new URL(req.url,'https://local.invalid'),path=(url.searchParams.has('route')?'/api/'+url.searchParams.get('route'):url.pathname).replace(/\/$/,'');
    if(!configured)return send(503,{error:'Your private Notion connection is not set up yet.',setupRequired:true});
    const origin=new URL(env.APP_ORIGIN).origin,jar=cookies(req),bearer=String(req.headers.authorization||'').replace(/^Bearer /,''),session=unseal(bearer||jar.cc_session,env.SESSION_KEY);
    const ids=env.PAGE_IDS.split(',').map(normalize);
    if(req.method==='POST'&&(!(req.headers.origin===origin||(req.headers.origin===consoleOrigin&&bearer))||!String(req.headers['content-type']).startsWith('application/json')))return send(403,{error:'Request not allowed.'});
    if(path==='/api/login'&&req.method==='GET'){
      if(session&&normalize(session.user)===normalize(env.ALLOWED_USER_ID)&&url.searchParams.get('console')==='1'){res.setHeader('Referrer-Policy','no-referrer');return redirect(consoleOrigin+'/notion-workspace/#session='+seal(session,env.SESSION_KEY));}
      const state=randomBytes(32).toString('hex');
      res.setHeader('Set-Cookie',cookie('cc_oauth',seal({state,console:url.searchParams.get('console')==='1',exp:Date.now()+600000},env.SESSION_KEY),600));
      const auth=new URL('https://api.notion.com/v1/oauth/authorize');
      for(const [k,v] of Object.entries({client_id:env.NOTION_CLIENT_ID,response_type:'code',owner:'user',redirect_uri:origin+'/api/callback',state}))auth.searchParams.set(k,v);
      return redirect(auth.href);
    }
    if(path==='/api/callback'&&req.method==='GET'){
      const state=unseal(jar.cc_oauth,env.SESSION_KEY);
      res.setHeader('Set-Cookie',cookie('cc_oauth','',0));
      if(!state||state.state!==url.searchParams.get('state')||!url.searchParams.get('code'))return redirect('/notion-workspace/?auth=failed');
      const r=await fetch('https://api.notion.com/v1/oauth/token',{method:'POST',headers:{Authorization:'Basic '+Buffer.from(env.NOTION_CLIENT_ID+':'+env.NOTION_CLIENT_SECRET).toString('base64'),'Content-Type':'application/json'},body:JSON.stringify({grant_type:'authorization_code',code:url.searchParams.get('code'),redirect_uri:origin+'/api/callback'}),signal:AbortSignal.timeout(15000)});
      if(!r.ok)return redirect('/notion-workspace/?auth=failed');
      const token=await r.json();
      if(normalize(token.owner?.user?.id)!==normalize(env.ALLOWED_USER_ID)||!token.access_token)return send(403,{error:'This workspace is private to its owner.'});
      const ticket=seal({token:token.access_token,user:token.owner.user.id,exp:Date.now()+3600000},env.SESSION_KEY);
      res.setHeader('Set-Cookie',[cookie('cc_oauth','',0),cookie('cc_session',ticket)]);
      res.setHeader('Referrer-Policy','no-referrer');
      if(state.console)return redirect(consoleOrigin+'/notion-workspace/#session='+ticket);
      return redirect('/notion-workspace/');
    }
    if(path==='/api/logout'&&req.method==='POST'){res.setHeader('Set-Cookie',cookie('cc_session','',0));return send(200,{ok:true});}
    if(!session||normalize(session.user)!==normalize(env.ALLOWED_USER_ID))return send(401,{error:'Sign in with Notion to open your pages.'});
    if(path==='/api/session'&&req.method==='GET')return send(200,{connected:true});
    const api=notionClient(session.token);
    if(path==='/api/pages'&&req.method==='GET'){
      const pages=[];
      for(const id of ids){try{const p=await api('pages/'+id);pages.push({id,title:Object.values(p.properties).find(p=>p.type==='title')?.title.map(t=>t.plain_text??t.text?.content??'').join('')||'Untitled',url:'https://www.notion.so/'+id});}catch(e){if(e.status===401)throw e;pages.push({id,title:'Page needs connection access',unavailable:true});}}
      return send(200,{pages});
    }
    const id=normalize(url.searchParams.get('id'));
    if(!ids.includes(id))return send(403,{error:'This page is not connected to Studio.'});
    if(path==='/api/page'&&req.method==='GET')return send(200,{blocks:await blocks(api,id)});
    if(path==='/api/save'&&req.method==='POST'){
      let body=req.body;
      if(!body){let raw='';for await(const part of req){raw+=part;if(raw.length>200000)return send(413,{error:'Save fewer changes at once.'});}body=JSON.parse(raw);}
      if(typeof body==='string')body=JSON.parse(body);
      if(JSON.stringify(body).length>200000)return send(413,{error:'Save fewer changes at once.'});
      return send(200,await save(api,id,body.changes));
    }
    return send(404,{error:'Not found.'});
  }catch(e){return send(e.status||500,{error:e.status?e.message:'The connection failed. Your draft is still here. Retry when connected.',saved:e.saved||[]});}
}
