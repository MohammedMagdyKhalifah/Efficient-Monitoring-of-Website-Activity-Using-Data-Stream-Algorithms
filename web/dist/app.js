import {downloadProject} from './download.js';

const $ = id => document.getElementById(id), $$ = selector => document.querySelectorAll(selector);
const nf = new Intl.NumberFormat('en-US',{maximumFractionDigits:1});
const fmt = n => nf.format(Number(n)||0), pct = (n,d=1) => `${(Number(n)*100).toFixed(d)}%`;
const short = n => n>=1e6?`${(n/1e6).toFixed(n>=1e7?0:1)}m`:n>=1000?`${(n/1000).toFixed(n>=10000?0:1)}k`:fmt(n);
const bytes = n => n>=1048576?`${(n/1048576).toFixed(1)} MiB`:n>=1024?`${(n/1024).toFixed(n%1024?1:0)} KiB`:`${fmt(n)} B`;
const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = (id,value) => { const element=$(id); if(element)element.textContent=value; };
const icons = {
  dashboard:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
  chart:'<path d="M4 3v17h17M8 15l4-5 4 2 5-7"/>',database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  book:'<path d="M3 4h6c2 0 3 1 3 3v14c0-2-1-3-3-3H3V4Zm18 0h-6c-2 0-3 1-3 3v14c0-2 1-3 3-3h6V4Z"/>',
  code:'<path d="m7 6-6 6 6 6M17 6l6 6-6 6M14 3l-4 18"/>',document:'<path d="M13 2H5v20h14V8l-6-6Z"/><path d="M13 2v6h6M8 13h8M8 17h6"/>',
  external:'<path d="M14 3h7v7m0-7L10 14M10 4H4v16h16v-6"/>',download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',play:'<path d="m8 4 12 8-12 8V4Z"/>',pause:'<path d="M8 4v16M16 4v16"/>',
  step:'<path d="m5 5 10 7-10 7V5ZM19 4v16"/>',reset:'<path d="M3 10a9 9 0 1 1 2 9M3 3v7h7"/>',
  activity:'<path d="M2 12h4l3-8 5 16 3-8h5"/>',users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 14a6 6 0 0 1 3 5v2"/>',
  filter:'<path d="M3 4h18l-7 8v7l-4 2v-9L3 4Z"/>',window:'<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M3 8h18M8 8v13"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',check:'<path d="m5 12 4 4L20 5"/>',copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
  flask:'<path d="M9 3h6M10 3v7L4 20c-.3 1 .3 1 1 1h14c.7 0 1.3 0 1-1l-6-10V3M8 15h8"/>'
};
function icon(name){return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name]||icons.activity}</svg>`;}
function installIcons(root=document){root.querySelectorAll('[data-icon]').forEach(e=>e.innerHTML=icon(e.dataset.icon));}
installIcons();

let manifest, catalog, benchmarks, worker, snapshot=null, state='loading', view='overview';
let history=[], feed=[], toastTimer, bitOffset=0, autoplay=false, sourceFiles=null;
let config={bits:1048576,k:7,h:16,window:10000,seed:42,limit:100000,rate:5000};
const colors={teal:'#178773',violet:'#a08acc',rose:'#cd9a8b',gray:'#b4bfc6',grid:'#edf1f2',text:'#a0adb2'};

function toast(message){text('toast',message);$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3200);}
function setState(next){
  state=next; const loading=next==='loading';
  $('play').disabled=loading; $('reset').disabled=loading; $('step').disabled=loading||next==='running'||next==='completed';
  text('play-text',loading?'Preparing data…':next==='running'?'Pause replay':next==='completed'?'Replay again':snapshot?.count?'Resume replay':'Start replay');
  $('play').querySelector('[data-icon]').innerHTML=icon(next==='running'?'pause':'play');
  const label={loading:'Loading',ready:'Ready',running:'Replaying',paused:'Paused',completed:'Complete',error:'Unavailable'}[next]||next;
  $('replay-status').className=`replay-status ${next==='running'?'running':''}`;
  $('replay-status').lastElementChild.textContent=label;
  $('chart-live').className=`live-indicator ${next==='running'?'running':''}`;
  $('chart-live').lastChild.textContent=label;
}
function clock(elapsed,full=false){
  if(!manifest)return '—';
  const d=new Date((manifest.epoch+elapsed-4*3600)*1000);
  const time=d.toISOString().slice(11,19);
  return full?`Jul ${d.getUTCDate().toString().padStart(2,'0')}, ${time} · UTC−04:00`:time;
}
function resetReplay(shouldPlay=false){
  autoplay=shouldPlay;history=[];feed=[];snapshot=null;bitOffset=0;
  setState('loading');$('error-notice').hidden=true;
  worker.postMessage({type:'init',config});
  renderEmpty();
}
function renderEmpty(){
  ['metric-requests','metric-unique','metric-window','fp-count','fm-legend','exact-legend','window-legend','window-exact-legend','feed-event-number'].forEach(id=>text(id,'0'));
  text('fp-count','0 false positives');text('requests-percent','0% complete');text('metric-fpr','0.00');
  text('unique-comparison','0 exact · 0% error');text('window-comparison',`0 exact · last ${short(config.window)}`);
  text('progress-text',`0 / ${fmt(config.limit)} requests`);$('progress-fill').style.width='0%';
  $('stream-progress').setAttribute('aria-valuenow','0');$('stream-progress').setAttribute('aria-valuemax',String(config.limit));
  text('stream-clock','Ready when you are');text('compute-time','Worker compute: 0 ms');
  $('request-rows').innerHTML='<tr><td colspan="5" class="empty-table">Waiting for the first request…</td></tr>';
  $('audience-empty').hidden=false;$('error-empty').hidden=false;text('feed-count','0');
  ['request-wave','unique-wave','window-wave'].forEach(id=>$(id).setAttribute('d','M0 23 L120 23'));
  drawCharts();
}
function appendHistory(points){
  for(const point of points){if(history.at(-1)?.n===point.n)history[history.length-1]=point;else history.push(point);}
}
function currentPoints(){
  const result=[{n:0,exact:0,fm:0,window:0,exactWindow:0,fpr:0},...history];
  if(snapshot?.count && result.at(-1).n!==snapshot.count)result.push({n:snapshot.count,exact:snapshot.unique,fm:snapshot.fm,window:snapshot.window,exactWindow:snapshot.exactWindow,fpr:snapshot.fpr});
  return result;
}
function miniWave(id,field){
  const points=currentPoints().slice(-25),max=Math.max(1,...points.map(v=>v[field]));
  $(id).setAttribute('d',points.map((p,i)=>`${i?'L':'M'}${(i/Math.max(1,points.length-1)*120).toFixed(1)} ${(23-p[field]/max*20).toFixed(1)}`).join(' '));
}
function render(data){
  snapshot=data.snapshot;appendHistory(data.history||[]);feed=data.feed||feed;
  if(data.state)setState(data.state);
  const s=snapshot;
  text('metric-requests',fmt(s.count));text('metric-unique',fmt(s.fm));text('metric-window',fmt(s.window));
  text('metric-fpr',(s.fpr*100).toFixed(2));text('requests-percent',`${Math.floor(s.count/config.limit*100)}% complete`);
  text('unique-comparison',`${fmt(s.unique)} exact · ${pct(s.fmError)} error`);
  text('window-comparison',`${fmt(s.exactWindow)} exact · last ${short(config.window)}`);
  text('fp-count',`${fmt(s.falsePositives)} false positives`);text('bloom-hashes',`${config.k} hashes`);
  text('fm-legend',fmt(s.fm));text('exact-legend',fmt(s.unique));text('window-legend',fmt(s.window));text('window-exact-legend',fmt(s.exactWindow));
  const progress=Math.min(100,s.count/config.limit*100);$('progress-fill').style.width=`${progress}%`;
  $('stream-progress').setAttribute('aria-valuenow',String(s.count));text('progress-text',`${fmt(s.count)} / ${fmt(config.limit)} requests`);
  text('stream-clock',s.last?clock(s.last.elapsed,true):'Ready when you are');
  $('bloom-fill').style.width=`${s.occupancy*100}%`;
  text('bloom-summary',`${fmt(config.bits)} bits · ${pct(s.occupancy,1)} occupied`);text('bloom-payload',bytes(config.bits/8));
  text('fm-summary',`${config.h} trailing-zero registers`);text('fm-payload',`${config.h} B`);
  text('dgim-summary',`${s.buckets.length} buckets in the window`);text('dgim-payload',bytes(s.buckets.length*8));
  text('compute-time',`Worker compute: ${Number(data.computeMs||0).toFixed(0)} ms`);
  text('feed-event-number',fmt(s.count));text('feed-count',feed.length);renderFeed();
  $('audience-empty').hidden=s.count>0;$('error-empty').hidden=s.count>0;
  miniWave('request-wave','n');miniWave('unique-wave','fm');miniWave('window-wave','window');
  $$('[data-window-label]').forEach(e=>e.textContent=fmt(config.window));
  if(view==='algorithms')renderAlgorithms();
  drawCharts();
}
function renderFeed(){
  if(!feed.length)return;
  $('request-rows').innerHTML=[...feed].reverse().map(e=>{
    const request=catalog.requests[e.request],host=catalog.hosts[e.host],statusClass=e.status>=500?'server-error':e.status>=400?'error':e.status>=300?'redirect':'';
    return `<tr data-event="${e.event}" tabindex="0" role="button" aria-label="Inspect request ${e.event}"><td>${clock(e.elapsed)}</td><td title="${esc(host)}">${esc(host)}</td><td class="request-path" title="${esc(request)}">${esc(request.replace(/ HTTP\/\S+$/,''))}</td><td><span class="status-pill ${statusClass}">${e.status}</span></td><td><span class="seen-pill ${e.falsePositive?'fp':e.prior?'':'new'}">${e.falsePositive?'False positive':e.prior?'Seen before':'New host'}</span></td></tr>`;
  }).join('');
}
function showRequest(number){
  const e=feed.find(r=>r.event===number);if(!e)return;
  $('request-detail').innerHTML=`<dl class="request-detail-list"><div><dt>Stream event</dt><dd>#${fmt(e.event)}</dd></div><div><dt>Original timestamp</dt><dd>${clock(e.elapsed,true)}</dd></div><div><dt>Originating host</dt><dd><code>${esc(catalog.hosts[e.host])}</code></dd></div><div><dt>Original request</dt><dd><code>${esc(catalog.requests[e.request])}</code></dd></div><div><dt>Server response / bytes</dt><dd>${e.status} / ${e.bytes===0xFFFFFFFF?'Unknown':fmt(e.bytes)}</dd></div><div><dt>Bloom decision before insertion</dt><dd>${e.bloomPresent?'Possibly seen':'Definitely new'} · exact: ${e.prior?'seen before':'not previously seen'}${e.falsePositive?' · FALSE POSITIVE':''}</dd></div><div><dt>Actual hash bit positions</dt><dd><code>${e.positions.join(', ')}</code></dd></div><div><dt>DGIM input bit</dt><dd>${e.bit} · ${e.bit?'HTTP error':'non-error response'}</dd></div></dl>`;
  $('request-dialog').showModal();
}
function renderAlgorithms(){
  const s=snapshot;if(!s)return;
  const hits=new Set(s.last?.positions||[]);text('bit-range',`${fmt(bitOffset)}–${fmt(bitOffset+127)}`);
  $('bit-grid').innerHTML=s.bits.map((bit,i)=>`<span class="bit-cell ${bit?'set':''} ${hits.has(bitOffset+i)?'highlight':''}" title="Bit ${bitOffset+i}: ${bit}">${bit}</span>`).join('');
  text('bloom-formula-stats',`m = ${fmt(config.bits)} · k = ${config.k} · d = ${fmt(s.unique)}`);
  text('bloom-fp-detail',fmt(s.falsePositives));text('bloom-fn-detail',fmt(s.falseNegatives));
  text('bloom-host',s.last?catalog.hosts[s.last.host]:'No host yet');
  text('bloom-live-result',s.last?s.last.falsePositive?'False positive':s.last.bloomPresent?'Possibly seen':'Definitely new':'Waiting for a request');
  text('bloom-explanation',s.last?`Event #${fmt(s.count)}: ${s.last.prior?'the exact set has seen this host.':'this host is new to the exact set.'} Bloom returned ${s.last.bloomPresent?'possibly present':'definitely absent'} before insertion.`:'Each hash selects a bit. Any zero proves absence; all ones mean possible membership.');
  $('hash-positions').innerHTML=(s.last?.positions||[]).map((p,i)=>`<span title="Hash low32: 0x${s.last.hashWords[i].toString(16).padStart(8,'0')}">h${i+1} → ${fmt(p)}</span>`).join('');
  const max=Math.max(8,...s.registers);$('registers').classList.toggle('many',config.h===64);
  $('registers').innerHTML=s.registers.map((r,i)=>`<div class="register" title="Hash ${i+1}: maximum trailing zeros ${r}; 2^R = ${fmt(2**r)}${s.last?`; incoming zeros ${s.last.zeros[i]}`:''}"><span class="register-value">${r}</span><div class="register-bar-track"><div class="register-bar" style="height:${r/max*100}%"></div></div><span class="register-label">h${i+1}</span></div>`).join('');
  text('fm-state-count',`${config.h} registers`);text('fm-group-means',s.count?`Group means: ${s.means.map(fmt).join(' · ')}`:'Group means: waiting for data');
  text('fm-detail-estimate',fmt(s.fm));text('fm-detail-exact',fmt(s.unique));text('fm-detail-error',pct(s.fmError,2));
  text('bucket-count',`${s.buckets.length} buckets`);
  $('bucket-strip').innerHTML=s.buckets.length?s.buckets.map((b,i)=>{
    const partial=i===s.buckets.length-1&&s.count>config.window&&b[0]>1;
    return `<div class="bucket ${partial?'partial':''}" title="${b[0]} ones, newest one at event ${b[1]}; age ${s.count-b[1]} requests"><b>${b[0]}</b><span>#${short(b[1])}</span>${partial?'<small>½ weight</small>':''}</div>`;
  }).join(''):'<div class="visual-empty">An error request will create the first bucket.</div>';
  $('binary-stream').innerHTML=(s.recentBits.length?s.recentBits:Array(128).fill(null)).map((b,i)=>`<span class="binary-bit ${b===1?'one':''}" title="${b===null?'No request yet':`Event ${s.count-s.recentBits.length+i+1}: ${b}`}">${b??'·'}</span>`).join('');
  text('dgim-detail-estimate',fmt(s.window));text('dgim-detail-exact',fmt(s.exactWindow));
  $('dgim-actions').innerHTML=s.actions.length?s.actions.map(a=>`<div><small>#${fmt(a.event)}</small>${esc(a.text)}</div>`).join(''):'Waiting for a bucket creation, merge or expiry.';
}

function baseCanvas(id){
  const canvas=$(id);if(!canvas || canvas.offsetWidth===0)return null;
  const r=canvas.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);
  canvas.width=Math.round(r.width*dpr);canvas.height=Math.round(r.height*dpr);
  const c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,r.width,r.height);c.font='9px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif';
  return {c,w:r.width,h:r.height,canvas};
}
function lineChart(id,series){
  const frame=baseCanvas(id);if(!frame)return;const {c,w,h}=frame;
  const p={l:43,r:12,t:17,b:35},pw=w-p.l-p.r,ph=h-p.t-p.b;
  const points=currentPoints(),xmax=Math.max(1,snapshot?.count||config.limit),rawMax=Math.max(1,...points.flatMap(d=>series.map(s=>d[s.key])));
  const order=10**Math.floor(Math.log10(rawMax)),ymax=Math.ceil(rawMax/order/0.5)*order*0.5;
  c.textAlign='right';c.fillStyle=colors.text;
  for(let i=0;i<=4;i++){const y=p.t+ph-i/4*ph;c.strokeStyle=colors.grid;c.beginPath();c.moveTo(p.l,y);c.lineTo(w-p.r,y);c.stroke();c.fillText(short(ymax*i/4),p.l-9,y+3);}
  c.textAlign='center';for(let i=0;i<=4;i++)c.fillText(short(xmax*i/4),p.l+pw*i/4,h-16);
  if(!snapshot?.count)return;
  for(const s of [...series].reverse()){
    if(s.area){const gradient=c.createLinearGradient(0,p.t,0,p.t+ph);gradient.addColorStop(0,s.color+'22');gradient.addColorStop(1,s.color+'00');c.beginPath();c.moveTo(p.l,p.t+ph);points.forEach(v=>c.lineTo(p.l+v.n/xmax*pw,p.t+ph-v[s.key]/ymax*ph));c.lineTo(p.l+pw,p.t+ph);c.closePath();c.fillStyle=gradient;c.fill();}
    c.beginPath();points.forEach((v,i)=>{const x=p.l+v.n/xmax*pw,y=p.t+ph-v[s.key]/ymax*ph;if(i)c.lineTo(x,y);else c.moveTo(x,y);});c.strokeStyle=s.color;c.lineWidth=1.8;c.stroke();
    const last=points.at(-1);c.beginPath();c.arc(p.l+last.n/xmax*pw,p.t+ph-last[s.key]/ymax*ph,2.8,0,Math.PI*2);c.fillStyle=s.color;c.fill();
  }
}
function barChart(id,rows,log=false){
  const frame=baseCanvas(id);if(!frame)return;const {c,w,h}=frame,p={l:49,r:15,t:16,b:38};
  const max=Math.max(1,...rows.flatMap(r=>[r.a,r.b??0])),top=log?Math.ceil(Math.log10(max)):max*1.1;
  const y=v=>p.t+(h-p.t-p.b)*(1-(log?(v>0?Math.log10(v):0):v)/top);
  c.textAlign='right';c.fillStyle=colors.text;
  const ticks=log?Array.from({length:Math.floor(top/2)+1},(_,i)=>i*2):[0,.25,.5,.75,1].map(v=>v*top);
  for(const tick of ticks){const yy=log?p.t+(h-p.t-p.b)*(1-tick/top):y(tick);c.beginPath();c.strokeStyle=colors.grid;c.moveTo(p.l,yy);c.lineTo(w-p.r,yy);c.stroke();c.fillStyle=colors.text;c.fillText(short(log?10**tick:tick),p.l-8,yy+3);}
  const available=w-p.l-p.r,step=available/rows.length;
  rows.forEach((r,i)=>{const groupX=p.l+step*(i+.5),width=Math.min(25,step*.23),paired=r.b!==undefined;
    c.fillStyle=colors.teal;c.beginPath();c.roundRect(groupX-(paired?width+3:width/2),y(r.a),width,Math.max(1,h-p.b-y(r.a)),[3,3,0,0]);c.fill();
    if(paired){c.fillStyle='#c3cfc8';c.beginPath();c.roundRect(groupX+3,y(r.b),width,Math.max(1,h-p.b-y(r.b)),[3,3,0,0]);c.fill();}
    c.textAlign='center';c.fillStyle=colors.text;c.font=`${rows.length>10?7:9}px -apple-system,sans-serif`;c.fillText(r.label,groupX,h-17);
  });
}
function drawCharts(){
  if(view==='overview'){
    lineChart('audience-chart',[{key:'fm',color:colors.violet,area:true},{key:'exact',color:colors.teal}]);
    lineChart('error-chart',[{key:'window',color:colors.rose,area:true},{key:'exactWindow',color:colors.gray}]);
  }
  if(view==='experiments'&&benchmarks){
    const max=Math.max(...benchmarks.scaling_summary.map(r=>Number(r.events)));
    const full=benchmarks.scaling_summary.filter(r=>Number(r.events)===max);
    barChart('memory-chart',full.map(r=>({label:{bloom:'Bloom',fm:'FM',dgim:'DGIM'}[r.algorithm],a:+r.state_bytes,b:+r.exact_state_bytes})),true);
    barChart('throughput-chart',full.map(r=>({label:{bloom:'Bloom',fm:'FM',dgim:'DGIM'}[r.algorithm],a:+r.throughput,b:+r.exact_throughput})),true);
  }
  if(view==='dataset'&&manifest){const days=Object.keys(manifest.daily_counts).sort((a,b)=>parseInt(a)-parseInt(b));barChart('daily-chart',days.map(d=>({label:String(parseInt(d)),a:manifest.daily_counts[d]})));}
}
function renderBenchmarks(){
  $('full-results').innerHTML=benchmarks.full_summary.map(r=>`<tr><td>${{bloom:'Bloom filter',fm:'Flajolet–Martin',dgim:'DGIM'}[r.algorithm]}</td><td>${r.algorithm==='bloom'?`${fmt(r.exact)} distinct hosts`:r.algorithm==='fm'?`${fmt(r.exact)} distinct hosts`:`${fmt(r.exact)} recent errors`}</td><td>${r.algorithm==='bloom'?`${r.false_positives} false positives`:`${fmt(r.estimate)}`}</td><td>${pct(r.relative_error,2)} ${r.algorithm==='bloom'?'online FPR':'relative error'}</td><td>${bytes(+r.state_bytes)}</td></tr>`).join('');
  const filter=$('experiment-filter').value;
  $('parameter-results').innerHTML=benchmarks.parameter_sweep.filter(r=>filter==='all'||r.algorithm===filter).map(r=>{
    const label=r.algorithm==='bloom'?`${fmt(r.bits)} bits / ${r.hashes} hashes`:r.algorithm==='fm'?`${r.hashes} hashes`:`${fmt(r.window)} requests`;
    const error=r.algorithm==='dgim'?r.mean_checkpoint_relative_error:r.relative_error;
    return `<tr><td>${{bloom:'Bloom',fm:'FM',dgim:'DGIM'}[r.algorithm]}</td><td>${label}</td><td>${r.algorithm==='dgim'?'—':r.seed}</td><td>${fmt(r.exact)}</td><td>${r.algorithm==='bloom'?`${r.false_positives} FP`:fmt(r.estimate)}</td><td>${pct(error,2)}</td><td>${bytes(+r.state_bytes)}</td></tr>`;
  }).join('');
}
function renderDataset(){
  text('dataset-checksum',manifest.sha256);
  $('status-distribution').innerHTML=Object.entries(manifest.statuses).sort((a,b)=>b[1]-a[1]).map(([code,n])=>`<div class="status-row"><span>${code}</span><div class="status-bar"><i style="width:${Math.max(.8,n/manifest.valid*100)}%"></i></div><b>${fmt(n)}</b></div>`).join('');
}
const views={overview:['Overview','A little memory. A lot of insight.','Follow real website activity as three algorithms turn a stream into a signal.'],algorithms:['Algorithm lab','See what the algorithms remember.','Every bit, register and bucket below is driven by the requests you replay.'],experiments:['Experiments','Measure the trade-off.','Accuracy, memory and processing time, measured on the original NASA stream.'],dataset:['The dataset','Start with something real.','A transparent source, an honest capture, and every event accounted for.']};
function navigate(){
  const candidate=location.hash.slice(1);view=views[candidate]?candidate:'overview';
  $$('[data-view]').forEach(e=>e.hidden=e.dataset.view!==view);
  $$('[data-nav]').forEach(e=>{e.classList.toggle('active',e.dataset.nav===view);if(e.dataset.nav===view)e.setAttribute('aria-current','page');else e.removeAttribute('aria-current');});
  const [crumb,title,description]=views[view];text('breadcrumb-current',crumb);text('page-title',title);text('page-description',description);
  document.title=`${crumb} · StreamLab`;closeNavigation();
  if(view==='algorithms')renderAlgorithms();requestAnimationFrame(drawCharts);
}
function closeNavigation(){document.querySelector('.app-shell').classList.remove('nav-open');$('nav-backdrop').hidden=true;$('menu-toggle').setAttribute('aria-expanded','false');}
window.addEventListener('hashchange',navigate);window.addEventListener('resize',()=>requestAnimationFrame(drawCharts));
$('menu-toggle').addEventListener('click',()=>{const open=document.querySelector('.app-shell').classList.toggle('nav-open');$('menu-toggle').setAttribute('aria-expanded',String(open));$('nav-backdrop').hidden=!open;});
$('nav-backdrop').addEventListener('click',closeNavigation);
$('play').addEventListener('click',()=>{
  if(state==='running'){worker.postMessage({type:'pause'});setState('paused');}
  else if(state==='completed')resetReplay(true);
  else {worker.postMessage({type:'play'});setState('running');}
});
$('step').addEventListener('click',()=>worker.postMessage({type:'step'}));
$('reset').addEventListener('click',()=>{resetReplay();toast('Replay reset. The next request will be the first genuine record.');});
$('speed').addEventListener('change',()=>{config.rate=+$('speed').value;worker?.postMessage({type:'speed',rate:config.rate});});
$('limit').addEventListener('change',()=>{config.limit=+$('limit').value;resetReplay();toast('Stream size changed. Replay restarted.');});
for(const [id,key] of [['bits-setting','bits'],['k-setting','k'],['h-setting','h'],['window-setting','window'],['seed-setting','seed']])$(id).addEventListener('change',()=>{config[key]=+$(id).value;resetReplay();toast('New parameters applied. Start or step through the new replay.');});
function moveBits(offset){bitOffset=Math.max(0,Math.min(config.bits-128,offset));worker?.postMessage({type:'bits',offset:bitOffset});}
$('bits-prev').addEventListener('click',()=>moveBits(bitOffset-128));$('bits-next').addEventListener('click',()=>moveBits(bitOffset+128));
$('bits-jump').addEventListener('click',()=>{if(snapshot?.last)moveBits(Math.floor(snapshot.last.positions[0]/128)*128);else toast('Process a request to inspect its hash positions.');});
$('request-rows').addEventListener('click',e=>{const row=e.target.closest('[data-event]');if(row)showRequest(+row.dataset.event);});
$('request-rows').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){const row=e.target.closest('[data-event]');if(row){e.preventDefault();showRequest(+row.dataset.event);}}});
$('open-guide').addEventListener('click',()=>{$('guide-dialog').showModal();closeNavigation();});
$$('[data-close]').forEach(button=>button.addEventListener('click',()=>$(button.dataset.close).close()));
$('experiment-filter').addEventListener('change',()=>{if(benchmarks)renderBenchmarks();});
async function copy(value){try{await navigator.clipboard.writeText(value);toast('Copied to clipboard.');}catch{toast('Clipboard access is unavailable. Select and copy the text directly.');}}
$('copy-checksum').addEventListener('click',()=>manifest&&copy(manifest.sha256));
$('open-source').addEventListener('click',async()=>{
  $('source-dialog').showModal();closeNavigation();
  try{if(!sourceFiles){const r=await fetch('./data/sources.json');if(!r.ok)throw Error('Source files are unavailable');sourceFiles=await r.json();$('source-file').innerHTML=Object.keys(sourceFiles).map(path=>`<option>${esc(path)}</option>`).join('');}showSource();}catch(e){text('source-content',e.message);}
});
function showSource(){const path=$('source-file').value;text('source-content',sourceFiles[path]);text('source-language',path.endsWith('.py')?'Python · complete source':path.endsWith('.js')?'JavaScript · complete source':path);}
$('source-file').addEventListener('change',showSource);$('copy-source').addEventListener('click',()=>sourceFiles&&copy(sourceFiles[$('source-file').value]));
$('download-project').addEventListener('click',async()=>{
  const button=$('download-project');button.disabled=true;toast('Preparing the complete project ZIP from its real source files…');
  try{await downloadProject(message=>toast(message));toast('Project ZIP ready. Your browser will save the download.');}catch(e){toast(`Download failed: ${e.message}`);}finally{button.disabled=false;}
});
$('audience-chart').addEventListener('mousemove',e=>{
  if(!snapshot?.count)return;const rect=e.currentTarget.getBoundingClientRect(),n=Math.max(0,(e.clientX-rect.left-43)/(rect.width-55))*snapshot.count;
  const point=currentPoints().reduce((best,p)=>Math.abs(p.n-n)<Math.abs(best.n-n)?p:best);
  const tip=$('audience-tooltip');tip.hidden=false;tip.textContent=`#${fmt(point.n)} requests · FM ${fmt(point.fm)} · exact ${fmt(point.exact)}`;
  tip.style.left=`${Math.max(5,Math.min(rect.width-220,e.clientX-rect.left-80))}px`;tip.style.top='15px';
});
$('audience-chart').addEventListener('mouseleave',()=>$('audience-tooltip').hidden=true);

async function load(){
  try{
    if(!('Worker' in window)||!('DecompressionStream' in window))throw Error('Please use a current browser with Web Workers and gzip stream support.');
    const [m,b,raw]=await Promise.all([fetch('./data/manifest.json'),fetch('./data/benchmarks.json'),fetch('./data/catalog.json.gz')]);
    if(!m.ok||!b.ok||!raw.ok)throw Error('Dataset assets could not be loaded. Serve this folder with python3 serve_web.py.');
    [manifest,benchmarks]=await Promise.all([m.json(),b.json()]);
    catalog=await new Response(raw.body.pipeThrough(new DecompressionStream('gzip'))).json();
    worker=new Worker('./worker.js',{type:'module'});
    worker.addEventListener('error',event=>fail(event.message||'The processing worker could not start.'));
    worker.addEventListener('message',({data})=>{
      if(data.type==='ready'){render({snapshot:data.snapshot,history:[],feed:[],state:'ready',computeMs:0});if(autoplay){autoplay=false;worker.postMessage({type:'play'});setState('running');}}
      else if(data.type==='update')render(data);
      else if(data.type==='completed'){setState('completed');toast(`Replay complete: ${fmt(snapshot.count)} real requests processed.`);}
      else if(data.type==='loading'){setState('loading');}
      else if(data.type==='error')fail(data.message);
    });
    renderBenchmarks();renderDataset();resetReplay();
  }catch(error){fail(error.message);}
}
function fail(message){setState('error');text('error-notice',message);$('error-notice').hidden=false;$('play').disabled=true;$('step').disabled=true;}
navigate();load();
