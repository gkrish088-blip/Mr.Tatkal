'use strict';
const $ = id => document.getElementById(id);
let state = {sessions:[], schedules:[], config:null, selected:null, view:'overview'};
let toastTimer, polling=false, initialized=false;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => String(value||'').replaceAll('_',' ');
function toast(message,error=false){ $('toast').textContent=message; $('toast').className='toast'+(error?' error':''); $('toast').hidden=false; clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500); }
async function api(path,options={}){
  const response=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json','X-Agent-Request':'1',...options.headers}});
  let data;try{data=await response.json();}catch{throw Error('Server returned an unreadable response');}
  if(!response.ok){
    if(response.status===401 && path!='/login'){$('application').hidden=true;$('login').hidden=false;}
    const detail=Array.isArray(data.detail)?data.detail.map(x=>x.msg).join('; '):data.detail;
    throw Error(detail||'Request failed');
  }return data;
}
const post=(path,data={})=>api(path,{method:'POST',body:JSON.stringify(data)});
function pill(status){const color=['completed','done'].includes(status)?'green':['failed','rejected','needs_reconciliation'].includes(status)?'red':['running','acting','waiting_human','pending','queued'].includes(status)?'orange':'neutral';return `<span class="pill ${color}">${esc(label(status).toUpperCase())}</span>`;}
function when(ts){return new Date(ts*1000).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}
function switchView(view){state.view=view;document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!=='view-'+view);document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.view===view));$('page-label').textContent=({overview:'Overview',sessions:'Sessions',schedules:'Schedules',settings:'Server settings'})[view];}
function readInputs(id){let result;try{result=JSON.parse($(id).value.trim()||'{}');}catch{throw Error('Task inputs must be valid JSON');}if(!result||Array.isArray(result)||typeof result!=='object')throw Error('Task inputs must be a JSON object');return result;}
function renderSessions(){
  $('nav-count').textContent=state.sessions.length;$('stat-sessions').textContent=state.sessions.length;
  $('stat-completed').textContent=state.sessions.filter(s=>s.status==='completed').length;
  const query=$('session-search').value.toLowerCase();
  const row=s=>`<button class="session-row" data-session="${esc(s.id)}"><span class="row-title"><span class="row-icon">${s.mode==='demo'?'▷':'↗'}</span><span class="row-text"><strong>${esc(s.goal)}</strong><small>${esc(s.mode==='demo'?'Local test':s.provider)} · ${esc(s.id.slice(0,8))}</small></span></span><span>${pill(s.status)}</span><span class="row-date">${esc(when(s.created))}</span></button>`;
  $('recent-list').innerHTML=state.sessions.slice(0,4).map(row).join('')||'<div class="list-empty">Your first session starts with a task above.</div>';
  $('all-sessions').innerHTML=state.sessions.filter(s=>(s.goal+' '+s.id).toLowerCase().includes(query)).map(row).join('')||'<div class="list-empty">No sessions to show yet.</div>';
}
function renderSchedules(){
  const active=state.schedules.filter(j=>j.status==='pending').length;
  $('stat-schedules').textContent=active;$('job-count').textContent=state.schedules.length;
  $('schedule-list').innerHTML=state.schedules.map(j=>`<article class="job">${pill(j.status)}<h3>${esc(j.goal)}</h3><code>${esc(j.cron||'ONE-TIME TASK')}</code><time>Next: ${esc(new Date(j.when*1000).toLocaleString(undefined,{timeZone:j.timezone||'UTC'}))} · ${esc(j.timezone||'UTC')}</time><span class="form-hint">${j.executions} execution${j.executions===1?'':'s'} · ${esc(j.inputs?.task?.mode==='demo'?'Local mock test':j.inputs?.task?.provider||'Default model')}</span><div class="job-actions">${j.status==='pending'?`<button data-job="${j.id}" data-action="pause">Pause</button>`:j.status==='paused'?`<button data-job="${j.id}" data-action="resume">Resume</button>`:''}${j.status!=='dispatching'?`<button class="delete" data-job="${j.id}" data-action="delete">Delete</button>`:'<span class="form-hint">Inspect sessions before reconciling uncertain dispatch.</span>'}</div></article>`).join('')||'<div class="empty-state"><div class="empty-illustration">◷</div><h3>Good timing starts here.</h3><p>Create your first schedule.<br>It stays saved across server restarts.</p></div>';
}
function renderConfig(){
  const c=state.config; const providers=Object.entries(c.providers);
  const options=providers.map(([key,p])=>`<option value="${key}">${key==='claude'?'Claude':'DeepSeek'}${p.configured?'':' · not configured'}</option>`).join('');
  const selected=$('provider').value||c.default_provider,scheduled=$('schedule-provider').value||c.default_provider;
  $('provider').innerHTML=options;$('schedule-provider').innerHTML=options;$('provider').value=selected;$('schedule-provider').value=scheduled;
  if(!initialized){
    const skills=c.skills.map(s=>`<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
    $('skill').insertAdjacentHTML('beforeend',skills);$('schedule-skill').insertAdjacentHTML('beforeend',skills);
    $('schedule-timezone').value=c.timezone; initialized=true;
  }
  $('timezone-small').textContent=c.timezone;
  $('model-note').textContent=providers.some(([,p])=>p.configured)?'Server credentials ready. No key needed in your browser.':'Add a model key to .env to run the general agent.';
  $('provider-cards').innerHTML=providers.map(([key,p])=>`<section class="card provider-card">${pill(p.configured?'configured':'not configured')}<h2>${key==='claude'?'Claude':'DeepSeek'}</h2><code>${esc(p.model)}</code><p>${p.configured?'Server key is configured.':`Add ${key==='claude'?'ANTHROPIC_API_KEY':'DEEPSEEK_API_KEY'} in .env.`}</p><button class="secondary small" data-check="${key}" ${p.configured?'':'disabled'}>Test connection ↗</button><p class="form-hint">Sends a small request using the server key.</p></section>`).join('');
  $('browser-setting').textContent=`Browser: ${c.browser.mode}${c.browser.headless?' · headless':''}. Configure BROWSER_ALLOWED_HOSTS before accessing other sites.`;
}
function artifactUrl(id,path){return '/api/sessions/'+encodeURIComponent(id)+'/artifacts/'+path.split('/').map(encodeURIComponent).join('/');}
async function renderDetail(){
  if(!state.selected)return;
  const s=await api('/sessions/'+state.selected);
  $('session-empty').hidden=true;$('session-panel').hidden=false;
  $('session-goal').textContent=s.goal;$('session-id').textContent=s.id;
  $('live-badge').outerHTML=`<span id="live-badge">${pill(s.requests.length?'waiting_human':s.status)}</span>`;
  $('session-steps').textContent=s.step+' steps';$('session-handoffs').textContent=s.handoffs+' handoffs';$('session-provider').textContent=s.mode==='demo'?'LOCAL MOCK · NO MODEL':s.provider.toUpperCase();
  $('stop-button').hidden=!['running','queued'].includes(s.status);$('resume-button').hidden=!['failed','blocked','cancelled','limit_reached'].includes(s.status)||s.pending_action;
  const problem=s.error||s.blocked_reason;
  $('session-error').hidden=!problem;$('session-error').textContent=problem||'';
  $('conversation').innerHTML=(s.messages||[]).map(m=>`<div class="message ${m.role==='assistant'?'assistant':'user'}"><strong>${m.role==='assistant'?'Agent':'You'}</strong><div>${esc(m.text)}</div></div>`).join('');
  $('followup-form').hidden=s.mode!=='agent'||!['completed','blocked','failed','cancelled','limit_reached'].includes(s.status)||s.pending_action;
  $('replay-link').hidden=!s.has_replay;$('replay-link').href=artifactUrl(s.id,'replay.html');
  let screenshot=[...s.events].reverse().find(e=>e.after?.screenshot)?.after.screenshot;
  if(screenshot){screenshot='steps/'+screenshot.replaceAll('\\','/').split('/').pop();}
  if(!screenshot)screenshot=s.artifacts.at(-1);
  $('screenshot').hidden=!screenshot;$('screenshot-placeholder').hidden=!!screenshot;
  if(screenshot){const url=artifactUrl(s.id,screenshot);if($('screenshot').getAttribute('src')!==url)$('screenshot').src=url;}
  $('timeline').innerHTML=[...s.events].reverse().slice(0,30).map(e=>`<li class="${e.result.ok?'':'failed'}"><span class="step-number">${e.phase==='plan'?'·':e.step}</span><span>${esc(e.reason)}<small>${esc(e.action.name)} · ${esc(e.tier)} · ${e.phase==='plan'?'model response':e.verification.verdict?'verified':'check failed'}</small></span></li>`).join('')||'<li>Waiting for the agent to begin.</li>';
  const box=$('handoff-box');box.hidden=!s.requests.length;
  const req=s.requests[0];
  if(req && box.dataset.request!==req.id){
    box.dataset.request=req.id;
    const approve=['approve','external_approval'].includes(req.kind);
    box.innerHTML=`<p><strong>${s.mode==='demo'?'LOCAL TEST APPROVAL':'HUMAN HANDOFF'}</strong></p><p>${esc(req.text)}</p>${s.mode==='demo'?'<p>This approves a fictional payment only. No money is moved.</p>':''}<div class="handoff-actions">${approve?`<button class="primary small" data-reply="approve" data-request="${req.id}">Approve ${s.mode==='demo'?'test':''}</button><button class="secondary small" data-reply="deny" data-request="${req.id}">Deny</button>`:req.kind==='choose'?req.options.map(o=>`<button class="secondary small" data-reply="${esc(o)}" data-request="${req.id}">${esc(o)}</button>`).join(''):`<input id="handoff-answer" aria-label="Reply to agent" placeholder="Your reply"><button class="primary small" data-reply-text="${req.id}">Send</button>`}</div>`;
  }else if(!req){box.dataset.request='';}
}
async function refresh(){
  if(polling||$('application').hidden)return;polling=true;
  try{
    [state.sessions,state.schedules]=await Promise.all([api('/sessions'),api('/schedules')]);
    renderSessions();renderSchedules();
    if(!state.selected && state.sessions.length)state.selected=state.sessions[0].id;
    await renderDetail();$('server-state').textContent='Server connected';$('server-state').classList.remove('offline');
  }catch(error){$('server-state').textContent='Connection interrupted';$('server-state').classList.add('offline');}
  finally{polling=false;}
}
async function boot(){
  const access=await api('/access');
  if(!access.authenticated){$('login').hidden=false;$('application').hidden=true;return;}
  $('login').hidden=true;$('application').hidden=false;$('logout').hidden=!access.required;
  state.config=await api('/status');renderConfig();await refresh();
}
document.addEventListener('click',async event=>{
  const view=event.target.closest('[data-view]');if(view){switchView(view.dataset.view);return;}
  const session=event.target.closest('[data-session]');if(session){state.selected=session.dataset.session;switchView('overview');await renderDetail();return;}
  const job=event.target.closest('[data-job]');
  const reply=event.target.closest('[data-reply]');const replyText=event.target.closest('[data-reply-text]');const check=event.target.closest('[data-check]');
  try{
    if(job){await post('/schedules/'+job.dataset.job+'/'+job.dataset.action);toast('Schedule updated');await refresh();}
    if(reply||replyText){const request=reply?.dataset.request||replyText.dataset.replyText;const value=reply?reply.dataset.reply:$('handoff-answer').value;await post('/sessions/'+state.selected+'/reply/'+request,{value});toast('Reply sent to the agent');await refresh();}
    if(check){check.disabled=true;check.textContent='Checking…';const result=await post('/check-model',{provider:check.dataset.check});toast('Connected to '+result.provider+' · '+result.latency_ms+' ms');check.textContent='Connection verified ✓';}
  }catch(error){toast(error.message,true);if(check){check.disabled=false;check.textContent='Test connection ↗';}}
});
$('run-form').addEventListener('submit',async event=>{event.preventDefault();$('run-button').disabled=true;try{const result=await post('/sessions',{goal:$('goal').value,provider:$('provider').value,skill:$('skill').value||null,inputs:readInputs('inputs')});state.selected=result.id;toast('Task queued');await refresh();}catch(error){toast(error.message,true);}finally{$('run-button').disabled=false;}});
$('demo-button').addEventListener('click',async()=>{$('demo-button').disabled=true;try{const result=await post('/sessions',{goal:'Rehearse a fictional booking from start to ticket',mode:'demo'});state.selected=result.id;switchView('overview');toast('Local test started. Approve the fictional payment when prompted.');await refresh();}catch(error){toast(error.message,true);}finally{$('demo-button').disabled=false;}});
$('stop-button').addEventListener('click',async()=>{try{await post('/sessions/'+state.selected+'/stop');toast('Stop requested');await refresh();}catch(error){toast(error.message,true);}});
$('resume-button').addEventListener('click',async()=>{try{await post('/sessions/'+state.selected+'/resume');toast('Session queued for resume');await refresh();}catch(error){toast(error.message,true);}});
$('followup-form').addEventListener('submit',async event=>{event.preventDefault();$('followup-button').disabled=true;try{await post('/sessions/'+state.selected+'/messages',{value:$('followup').value});$('followup').value='';await refresh();}catch(error){toast(error.message,true);}finally{$('followup-button').disabled=false;}});
$('schedule-kind').addEventListener('change',()=>{const cron=$('schedule-kind').value==='cron';$('once-fields').hidden=cron;$('cron-fields').hidden=!cron;});
$('schedule-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{const result=await post('/schedules',{goal:$('schedule-goal').value,mode:$('schedule-mode').value,provider:$('schedule-provider').value,skill:$('schedule-skill').value||null,inputs:readInputs('schedule-inputs'),kind:$('schedule-kind').value,when:$('schedule-when').value||null,cron:$('schedule-cron').value,timezone:$('schedule-timezone').value});toast('Schedule saved · '+result.timezone);await refresh();}catch(error){toast(error.message,true);}finally{button.disabled=false;}});
$('session-search').addEventListener('input',renderSessions);
$('login-form').addEventListener('submit',async event=>{event.preventDefault();try{await post('/login',{password:$('password').value});$('password').value='';$('login-error').textContent='';await boot();}catch(error){$('login-error').textContent=error.message;}});
$('logout').addEventListener('click',async()=>{await post('/logout');$('application').hidden=true;$('login').hidden=false;});
boot().catch(error=>toast(error.message,true));setInterval(refresh,1500);
