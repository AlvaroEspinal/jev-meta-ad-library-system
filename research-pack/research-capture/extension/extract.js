// Self-contained injected function. Never fetch, click, read form values, cookies, or hidden metadata.
export function extractVisible(){
 const host=location.hostname.toLowerCase().replace(/\.+$/,'');
 if(host==='instagram.com'||host.endsWith('.instagram.com'))throw Error('Instagram DOM capture is prohibited.');
 const visible=e=>Boolean(e&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).display!=='none');
 const safe=e=>!e.closest('input,textarea,select,[contenteditable="true"],form,[hidden],[aria-hidden="true"]');
 const txt=e=>visible(e)&&safe(e)?e.innerText.trim().slice(0,30000):'';
 const first=(root,sel)=>[...root.querySelectorAll(sel)].find(e=>visible(e)&&safe(e));
 const fields={title:document.title,identity:'',source_id:'',primary_text:'',headline:'',subheadline:'',cta:'',landing_url:'',published_at:'',transcript:'',notes:'',active_status:'',advertiser_id:'',format:''};
 let root=document,media=[];
 const selection=window.getSelection();
 if(selection?.rangeCount){const range=selection.getRangeAt(0),el=range.commonAncestorContainer.nodeType===1?range.commonAncestorContainer:range.commonAncestorContainer.parentElement;if(el&&safe(el))fields.primary_text=selection.toString().slice(0,30000);}
 if(['www.facebook.com','facebook.com'].includes(host)&&(location.pathname==='/ads/library'||location.pathname.startsWith('/ads/library/'))){
  if(location.pathname!=='/ads/library'&&!location.pathname.startsWith('/ads/library/'))throw Error('Not Ad Library');
  const candidates=[...document.querySelectorAll('[role="article"],article,[data-research-ad]')].filter(visible);
  const wanted=new URL(location.href).searchParams.get('id');
  root=candidates.find(e=>wanted&&e.innerText.includes(wanted))||(candidates.length===1?candidates[0]:null);
  if(!root)throw Error('Cannot safely isolate one ad. Open a single ad or use manual capture; no mixed-ad copy will be saved.');
  const body=txt(root),id=body.match(/(?:Library ID|Ad ID)\s*:?\s*(\d+)/i);
  fields.source_id=id?.[1]||wanted||'';
  fields.active_status=/^Active$/m.test(body)?'Active':/^Inactive$/m.test(body)?'Inactive':'';
  fields.published_at=(body.match(/Started running on ([^\n]+)/)||[])[1]||'';
  fields.advertiser_id=new URL(location.href).searchParams.get('view_all_page_id')||'';
  fields.format=first(root,'video')?'video':first(root,'img')?'image':'';
  fields.identity=txt(first(root,'[data-research-identity],h2,h3'));
  fields.primary_text=fields.primary_text||txt(first(root,'[data-research-copy],p'));
  fields.headline=txt(first(root,'[data-research-headline],h4'));
  fields.subheadline=txt(first(root,'[data-research-subheadline]'));
  fields.cta=txt([...root.querySelectorAll('a,button,[role="button"]')].find(e=>visible(e)&&/^(Learn more|Book now|Get quote|See details|Contact us|Shop now|Sign up|Send message)$/i.test(e.innerText.trim())));
  fields.landing_url=[...root.querySelectorAll('a[href]')].find(e=>visible(e)&&/^https?:/.test(e.href)&&!/(^|\.)facebook\.com$/.test(new URL(e.href).hostname))?.href||'';
 }else if(['www.youtube.com','youtube.com','m.youtube.com','youtu.be'].includes(host)){
  const u=new URL(location.href);fields.source_id=u.searchParams.get('v')||(u.pathname.match(/\/(?:shorts|live)\/([\w-]+)/)||[])[1]||'';
  fields.title=txt(first(document,'h1 yt-formatted-string,h1'))||fields.title;
  fields.identity=txt(first(document,'ytd-channel-name a,#owner #channel-name a,[data-research-identity]'));
  fields.primary_text=fields.primary_text||txt(first(document,'#description-inline-expander,#description'));
  fields.published_at=txt(first(document,'#info-strings yt-formatted-string,time'));
  // User must explicitly open transcript themselves. Only currently rendered segments.
  fields.transcript=[...document.querySelectorAll('ytd-transcript-segment-renderer')].filter(visible).map(txt).join('\n').slice(0,30000);
 }else{
  fields.title=txt(first(document,'h1'))||fields.title;
  fields.primary_text=fields.primary_text||[...document.querySelectorAll('main p,article p')].filter(e=>visible(e)&&safe(e)).map(txt).join('\n').slice(0,30000);
  fields.identity=txt(first(document,'[rel="author"],.author'));
 }
 for(const el of root.querySelectorAll('video,audio,img')){
  if(!visible(el)||!safe(el))continue; const src=el.currentSrc||el.src;
  if(src&&/^https?:/.test(src)&&media.length<20)media.push(src);
 }
 return {fields,media_references:[...new Set(media)],observed_url:location.href};
}
