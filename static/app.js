const $ = (id) => document.getElementById(id);
const notice = (msg, error=false) => { $('notice').textContent = msg; $('notice').className = error ? 'error' : 'success'; };
async function api(path, opts={}) {
  const res = await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  if (!res.ok) { let body={}; try { body=await res.json(); } catch {} throw new Error(body.error || `Request failed (${res.status})`); }
  return res.status===204 ? null : res.json();
}
function td(text) { const e=document.createElement('td'); e.textContent=String(text ?? '—'); return e; }
function action(label, handler, kind='secondary') { const b=document.createElement('button'); b.textContent=label; b.className=kind+' small'; b.addEventListener('click',handler); return b; }
async function refresh() {
  try {
    const [devices,summary] = await Promise.all([api('/api/devices'),api('/api/summary')]);
    for (const key of ['total','up','down','unchecked']) $(key).textContent=summary[key];
    const tbody=$('devices'); tbody.replaceChildren();
    if (!devices.length) { const tr=document.createElement('tr'); const cell=td('No devices yet. Add one above to get started.'); cell.colSpan=6; tr.append(cell); tbody.append(tr); return; }
    for (const d of devices) {
      const tr=document.createElement('tr');
      tr.append(td(d.name),td(`${d.host}:${d.port}`),td(d.location || '—'));
      const s=td(d.latest_check?.status || 'unchecked'); s.className='state '+(d.latest_check?.status || 'unchecked'); tr.append(s);
      tr.append(td(d.latest_check?.checked_at ? new Date(d.latest_check.checked_at).toLocaleString() : 'Never'));
      const actions=td(''); actions.className='actions';
      actions.append(action('Check',async()=>{ try { notice('Checking '+d.name+'…'); await api(`/api/devices/${d.id}/check`,{method:'POST'}); notice('Check completed for '+d.name); await refresh(); } catch(e){notice(e.message,true);} }));
      actions.append(action('History',async()=>{try{const history=await api(`/api/devices/${d.id}/checks`); alert(history.length ? history.map(h=>`${h.checked_at}: ${h.status.toUpperCase()} (${h.latency_ms} ms)`).join('\n') : 'No checks yet');}catch(e){notice(e.message,true);}}));
      actions.append(action('Config',async()=>{const content=prompt('Enter a configuration snapshot for '+d.name+' (stored only; never executed):'); if(content===null)return;try{await api(`/api/devices/${d.id}/configurations`,{method:'POST',body:JSON.stringify({content})});notice('Configuration snapshot saved');}catch(e){notice(e.message,true);}}));
      actions.append(action('Delete',async()=>{if(!confirm(`Delete ${d.name} and its history?`))return;try{await api(`/api/devices/${d.id}`,{method:'DELETE'});notice('Device deleted');await refresh();}catch(e){notice(e.message,true);}},'danger'));
      tr.append(actions); tbody.append(tr);
    }
  } catch(e) { notice(e.message,true); }
}
$('device-form').addEventListener('submit',async(e)=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target).entries());data.port=Number(data.port);try{await api('/api/devices',{method:'POST',body:JSON.stringify(data)});e.target.reset();notice('Device added');await refresh();}catch(err){notice(err.message,true);}});
$('refresh').addEventListener('click',refresh);refresh();
