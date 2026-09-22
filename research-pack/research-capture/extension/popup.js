import {HOST,cleanURL,classify,redact} from './policy.js';
import {extractVisible} from './extract.js';
const ids=['title','identity','source_id','primary_text','headline','subheadline','cta','landing_url','published_at','transcript','notes','active_status','advertiser_id','format'];
const $=id=>document.getElementById(id);let target=null,method='manual',observedURL=null;let allowedOrigins=[];let externalSource=false;
function status(s,error=false){$('status').textContent=s;$('status').dataset.error=String(error);}
function mode(){try{const kind=classify($('source').value),ig=kind==='instagram_handoff';$('review').hidden=ig;$('screen-label').hidden=ig;$('preview').disabled=ig;$('meta-consent').hidden=!['meta_ad_library','facebook'].includes(kind);$('save').textContent=ig?'Save external URL reference':'Save to Obsidian';if(ig)status('Instagram: paste an external URL only. Assets require the approved non-browser import utility; no browser collection or fallback.');return kind;}catch(e){status(e.message,true);return null;}}
function consent(kind){if(!$('public').checked)throw Error('Confirm the content is public and authorized.');if(['meta_ad_library','facebook'].includes(kind)&&!$('isolated').checked)throw Error('Use an isolated, logged-out browser for Meta and confirm it.');}
async function active(){const [t]=await chrome.tabs.query({active:true,currentWindow:true});if(!target||t?.id!==target.id||cleanURL(t.url)!==cleanURL(target.url))throw Error('Active page changed. Reopen the capture popup.');return t;}
async function busy(fn){$('save').disabled=true;$('download').disabled=true;$('preview').disabled=true;try{await fn();}catch(e){status(e.message,true);}finally{$('save').disabled=false;$('download').disabled=false;try{$('preview').disabled=classify($('source').value)==='instagram_handoff';}catch{$('preview').disabled=true;}}}
$('source').addEventListener('change',()=>{externalSource=true;method='manual';observedURL=null;for(const k of ids)$ (k).value='';$('media').value='';mode();});
$('preview').addEventListener('click',()=>busy(async()=>{
 const kind=classify($('source').value);if(kind==='instagram_handoff')throw Error('Instagram DOM capture blocked.');consent(kind);
 if(!allowedOrigins.includes(new URL($('source').value).origin))throw Error('Origin not approved for DOM capture. Use manual entry or explicitly configure this origin locally.');
 const t=await active();if(cleanURL(t.url)!==cleanURL($('source').value))throw Error('For a different URL use manual entry; the current page will not be read.');
 const [result]=await chrome.scripting.executeScript({target:{tabId:t.id},func:extractVisible});
 if(!result?.result)throw Error('No readable evidence; use manual capture.');
 if(cleanURL(result.result.observed_url)!==cleanURL(t.url))throw Error('Navigation changed during capture. Reopen and review.');
 for(const k of ids)$(k).value=redact(result.result.fields[k]);
 $('media').value=result.result.media_references.map(u=>{try{return cleanURL(u);}catch{return '';}}).filter(Boolean).join('\n');
 observedURL=cleanURL(t.url);method='visible-dom';status('Evidence read. Review fields and remove anything private before saving.');
}));
$('save').addEventListener('click',()=>busy(async()=>{
 const source=cleanURL($('source').value),kind=classify(source);consent(kind);
 const fields={};for(const k of ids)fields[k]=redact($(k).value.trim());
 let screenshot=null,refs=$('media').value.split('\n').map(s=>s.trim()).filter(Boolean).map(cleanURL);
 if(kind==='instagram_handoff'){if(!externalSource)throw Error('Paste an external Instagram URL; active-tab capture is prohibited.');for(const k of ids)if(k!=='notes')delete fields[k];refs=[];method='instagram-url-handoff';}
 else if(method==='visible-dom'&&source!==observedURL)throw Error('Source changed after extraction; clear fields and review again.');
 if(kind!=='instagram_handoff'&&$('screenshot').checked){
  if($('rights').value==='reference-only')throw Error('Choose a valid capture rights basis before including a screenshot.');
  if(!allowedOrigins.includes(new URL(source).origin))throw Error('Origin not approved for screenshot capture.');
  const t=await active();if(cleanURL(t.url)!==source)throw Error('Screenshot must match the reviewed source.');
  if(classify(t.url)==='instagram_handoff')throw Error('Instagram screenshots blocked.');
  screenshot=await chrome.tabs.captureVisibleTab(t.windowId,{format:'png'});await active();
 }
 const payload={schema_version:1,capture_id:crypto.randomUUID(),captured_at:new Date().toISOString(),source_url:source,project:$('project').value,rights_basis:$('rights').value,fields,media_references:refs,screenshot,method,consent:{confirmed:true,public_only:true,isolated_logged_out:$('isolated').checked,screenshot:Boolean(screenshot)}};
 status('Saving locally…');
 const useWorkflow=kind!=='instagram_handoff'&&!screenshot;
 const message=useWorkflow?{command:'workflow',mode:'save_obsidian',payload,asset_url:$('asset').value.trim(),title:$('asset-title').value,convert:$('convert').value,fetch_landing:$('fetch-landing').checked}:{command:'capture',payload};
 if(screenshot&&$('asset').value.trim())throw Error('Save the downloaded asset separately from a viewport screenshot.');
 const receipt=await chrome.runtime.sendNativeMessage(HOST,message);
 $('receipt').textContent=JSON.stringify(receipt,null,2);if(!receipt.ok)throw Error(receipt.error||'Local save failed. Nothing claimed as captured.');
 status(`${receipt.status.toUpperCase()} · ${receipt.id}`);await chrome.storage.local.set({project:$('project').value});
}));
$('download').addEventListener('click',()=>busy(async()=>{
 const source=cleanURL($('source').value),kind=classify(source);consent(kind);
 if(kind==='instagram_handoff')throw Error('Use the approved external non-browser import utility for Instagram media.');
 const payload={schema_version:1,capture_id:crypto.randomUUID(),captured_at:new Date().toISOString(),source_url:source,project:$('project').value,rights_basis:$('rights').value,fields:{title:$('title').value,notes:$('notes').value},media_references:[],method:'manual',consent:{confirmed:true,public_only:true,isolated_logged_out:$('isolated').checked}};
 status('Downloading selected asset locally…');const receipt=await chrome.runtime.sendNativeMessage(HOST,{command:'workflow',mode:'quick_download',payload,asset_url:$('asset').value.trim(),title:$('asset-title').value,convert:$('convert').value});
 $('receipt').textContent=JSON.stringify(receipt,null,2);if(!receipt.ok)throw Error(receipt.error);status('DOWNLOADED · Downloads only; no Obsidian write');
}));
try{[target]=await chrome.tabs.query({active:true,currentWindow:true});if(classify(target?.url||'')==='instagram_handoff'){target=null;$('source').value='';}else $('source').value=cleanURL(target?.url||'');const settings=await chrome.storage.local.get('project');$('project').value=settings.project||'research';mode();const h=await chrome.runtime.sendNativeMessage(HOST,{command:'health'});if(!h.ok)throw Error(h.error);allowedOrigins=h.allowed_capture_origins||[];status('Local companion ready. Review and confirm public evidence.');mode();}catch(e){status(`Setup/source check: ${e.message}. Manual entry is available; saving requires the companion.`,true);}
