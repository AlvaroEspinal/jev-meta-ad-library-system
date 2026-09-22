const $ = id => document.getElementById(id);
let latestRevision = -1;
function n(v){return Number(v || 0).toLocaleString()}
function text(el, value){el.textContent = value ?? ''}
function statusName(value){return String(value || 'waiting').replaceAll('_',' ')}
function render(state){
  if (!state || state.revision === latestRevision && false) return;
  latestRevision = state.revision;
  const totals=state.totals||{}; text($('runs'),n(totals.runs)); text($('ads'),n(totals.observed_ads)); text($('complete'),n(totals.completed_workers)); text($('issues'),n((totals.blocked_workers||0)+(totals.failed_workers||0))); text($('revision'),`Revision ${state.revision||0}`);
  const run=state.active_run; const fixture=$('fixture'); fixture.hidden=!run?.synthetic;
  if(!run){text($('run-name'),'No receipts yet'); text($('run-meta'),'Start the cockpit, then configure the runner with its loopback URL and token.'); $('workers').replaceChildren(); $('run-status').className='badge idle';text($('run-status'),'Waiting'); renderHistory(state.runs||[]);return}
  text($('run-name'),run.run_id); text($('run-meta'),`${run.summary.workers||0} configured workers · ${n(run.summary.observed_ads)} observed ads · updated ${new Date(run.updated_at).toLocaleString()}`); const badge=$('run-status');badge.className=`badge ${run.status}`;text(badge,statusName(run.status));
  const workers=$('workers');workers.replaceChildren(); for(const w of run.workers||[]){const card=document.createElement('article');card.className='worker'; const top=document.createElement('div');top.className='worker-top';const id=document.createElement('span');id.className='worker-id';text(id,w.worker_id);const s=document.createElement('span');s.className=`badge ${w.status}`;text(s,statusName(w.status));top.append(id,s);card.append(top);const company=document.createElement('p');company.className='company';text(company,w.company||'Company not supplied');card.append(company);const ads=document.createElement('p');ads.className='observed';ads.textContent=n(w.observed_ads);const small=document.createElement('small');small.textContent=' visible ID observations';ads.append(document.createElement('br'),small);card.append(ads);const detail=document.createElement('p');detail.className='detail';text(detail,w.url||w.detail?.message||'No URL or note received');card.append(detail);workers.append(card)}
  renderHistory(state.runs||[]);
}
function renderHistory(runs){const list=$('history');list.replaceChildren();if(!runs.length){const p=document.createElement('p');p.className='muted';text(p,'No completed or active runs have been received.');list.append(p);return}for(const run of runs){const row=document.createElement('div');row.className='history-row';const id=document.createElement('span');text(id,run.run_id);const ads=document.createElement('span');text(ads,`${n(run.summary.observed_ads)} visible IDs`);const status=document.createElement('span');status.className=`badge ${run.status}`;text(status,statusName(run.status));const when=document.createElement('span');when.className='when muted';text(when,new Date(run.updated_at).toLocaleString());row.append(id,ads,status,when);list.append(row)}}
function live(){const source=new EventSource('/api/events/stream');source.addEventListener('state',event=>{try{render(JSON.parse(event.data));$('dot').className='dot live';text($('connection'),'Live updates')}catch{}});source.onerror=()=>{source.close();$('dot').className='dot';text($('connection'),'Polling');poll()}}
function poll(){fetch('/api/state',{cache:'no-store'}).then(r=>r.json()).then(render).catch(()=>{text($('connection'),'Waiting for server')}).finally(()=>setTimeout(poll,2500))}
live();
