'use strict';
let state=null,tab='overview',query='',bomTab='ebom',busy=false;
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const value=x=>typeof x==='object'?JSON.stringify(x):String(x??'—');
const tag=x=>`<span class="tag" data-status="${esc(x)}">${esc(x??'NOT_DECLARED')}</span>`;
const empty=x=>`<div class="empty">${esc(x)}</div>`;
const raw=x=>`<details><summary>Исходная запись</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details>`;
const matches=x=>!query||JSON.stringify(x).toLowerCase().includes(query);
const fileLink=(id,text)=>id?`<a href="/artifact?id=${encodeURIComponent(id)}" target="_blank" rel="noopener">${esc(text)}</a>`:'';
function card(x){return `<article class="card"><div class="card-head"><h3>${esc(x.id||x.node||x.name||'Запись')} ${esc(x.title||'')}</h3>${tag(x.status)}</div>${(x.reasons||[]).map(r=>`<div class="reason">${esc(value(r))}</div>`).join('')||'<p class="muted">Причина не передана источником.</p>'}${x.next_action?`<p>Следующий шаг: ${esc(value(x.next_action))}</p>`:''}${x.depends_on?`<p class="muted">Зависит от: ${esc(value(x.depends_on))}</p>`:''}${raw(x)}</article>`}
function render(){if(!state)return;
 $('overall').innerHTML=tag(state.overall);$('date').textContent=state.generated_utc||'Источник не передал дату';$('fresh').textContent=value(state.freshness);
 const issues=Object.entries(state.sources).filter(([,s])=>s.state!=='AVAILABLE').map(([k,s])=>`${k}: ${s.state}${s.error?' — '+s.error:''}`);
 const changed=state.input_checks.filter(x=>x.state!=='MATCH');
 $('integrity').innerHTML=(issues.length?`<div class="notice">${issues.map(esc).join('<br>')}</div>`:'')+(changed.length?`<div class="notice">Проверка файлов входов: ${esc(changed.map(x=>x.path+' — '+x.state).join('; '))}. Показанный вердикт сохранённого источника не пересчитывался центром.</div>`:'')+(!state.input_checks.length?'<p class="muted">Источник не передал физические хеши входов для проверки свежести.</p>':'');
 $('commands').innerHTML=state.commands.map(c=>`<button data-command="${esc(c)}" ${busy?'disabled':''}>${esc(c==='verdict'?'Пересчитать вердикт':c==='audit'?'Проверить структуру':c==='selftest'?'Проверить систему':c)}</button>`).join('');
 let html='';
 if(tab==='overview'){html='<h2>Что блокирует следующий результат</h2>'+state.blockers.filter(matches).map(card).join('');if(!state.blockers.filter(matches).length)html+=empty(query?'Нет совпадений.':'Источник не передал блокеры. Это само по себе не подтверждает готовность изделия.');}
 if(tab==='graph'){
  html=['nodes','requirements','gates'].map((k,i)=>`<h2>${['Узлы и зависимости','Требования','Гейты'][i]}</h2>`+(state.groups[k].filter(matches).map(card).join('')||empty('Записи не переданы выбранным источником.'))).join('');
  html+='<h2>Структура графа</h2>'+raw(state.graph);
 }
 if(tab==='bom'){
  const b=state.boms[bomTab],rows=b.rows.filter(matches),s=state.sources[bomTab];
  html=`<div class="section-tabs"><button data-bom="ebom">EBOM</button><button data-bom="mbom">MBOM</button></div><p>${tag(b.status)} · Строк в документе: ${b.rows.length} · ${fileLink(s.file_id,'Открыть источник')}</p>`+b.reasons.map(r=>`<div class="reason">${esc(value(r))}</div>`).join('');
  const fields=[['PartNo','part_no','id'],['Description','description','name'],['Qty','qty','quantity'],['Material','material_authority','material'],['MakeBuy','make_buy','makebuy'],['Supplier','supplier'],['release_status','release','status']];
  html+=rows.length?`<div class="table-wrap"><table><thead><tr>${['Позиция','Наименование','Количество','Материал','Изготовить / купить','Поставщик','Статус'].map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>'<tr>'+fields.map((fs,i)=>{const v=fs.map(f=>r[f]).find(v=>v!==undefined&&v!==null);return `<td>${i===6?tag(v):esc(value(v))}</td>`}).join('')+'</tr>').join('')}</tbody></table></div>`:empty('Строки спецификации отсутствуют или не соответствуют поиску.');
  if(b.transformations.length)html+='<h2>Производственные преобразования</h2>'+raw(b.transformations);
 }
 if(tab==='artifacts'){
  html='<h2>Чертежи, расчёты и исходные документы</h2>'+state.artifacts.filter(matches).map(a=>`<article class="card"><div class="card-head"><h3>${esc(a.id||a.name||a.path)}</h3>${tag(a.availability)}</div><p>${esc(a.path||a.file_path||'Путь не передан')}</p><p>Статус источника: ${tag(a.status)}</p><div class="links">${fileLink(a.file_id,'Открыть / скачать')}${a.file_id&&['.pdf','.png','.jpg','.jpeg','.bmp'].includes(a.extension)?`<button data-preview="${esc(a.file_id)}" data-ext="${esc(a.extension)}">Показать</button>`:''}</div><div id="preview-${esc(a.file_id)}"></div>${raw(a)}</article>`).join('');if(!state.artifacts.filter(matches).length)html+=empty('В реестре нет доступных записей. Пути к документам должны быть переданы в evidence index.');
 }
 if(tab==='history')html='<h2>Журнал диспетчера</h2><p class="muted">Последние 200 записей. Код возврата показывается без переинтерпретации в инженерный PASS. Целостность цепочки этим представлением не подтверждается.</p>'+state.history_errors.map(x=>`<div class="notice">${esc(x)}</div>`).join('')+(state.history.filter(matches).map(x=>`<article class="card"><h3>${esc(x.command||x.event||x.id||'Событие')}</h3><p>${esc(x.utc||x.generated_utc||'Дата не указана')} · код ${esc(x.returncode??'—')}</p>${raw(x)}</article>`).join('')||empty('История запусков отсутствует.'));
 if(tab==='history')html='<h2>Версии Git</h2>'+raw(state.git)+html;
 if(tab==='sources')html='<h2>Источники и физические версии файлов</h2><p class="muted">Показанные SHA-256 идентифицируют файлы. Семантические хеши и инженерная свежесть принимаются только из данных движка.</p>'+Object.entries(state.sources).filter(matches).map(([k,s])=>`<article class="card"><div class="card-head"><h3>${esc(k)}</h3>${tag(s.state)}</div><p>${esc(s.path)}</p><p class="muted">Изменён: ${esc(s.modified||'—')}</p><pre>${esc(s.sha256||'Хеш отсутствует')}</pre>${fileLink(s.file_id,'Открыть документ')}${s.error?`<div class="reason">${esc(s.error)}</div>`:''}</article>`).join('');
 $('content').innerHTML=html;$('footer').textContent=state.repo_root+' · Только данные выбранных источников';
}
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);state=await r.json();$('error').hidden=true;render()}catch(e){$('error').hidden=false;$('error').textContent='Данные не обновлены: '+e.message+'. Последний отображённый результат не является новым расчётом.'}}
async function run(command){busy=true;render();$('job').hidden=false;$('jobstate').textContent='Запуск '+command;$('joboutput').textContent='';try{const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-K01-Token':state.token},body:JSON.stringify({command})});const x=await r.json();if(!r.ok)throw Error(x.error||r.status);poll(x.id)}catch(e){$('jobstate').textContent=e.message;busy=false;render()}}
async function poll(id){try{const r=await fetch('/api/jobs');if(!r.ok)throw Error('HTTP '+r.status);const j=(await r.json())[id];if(!j)throw Error('Запуск не найден');$('jobstate').textContent=j.command+' · '+j.state+(j.returncode!==null?' · код '+j.returncode:'');$('joboutput').textContent=j.output||'Команда выполняется; журнал появится после завершения.';if(j.state==='RUNNING')setTimeout(()=>poll(id),1000);else{busy=false;await refresh()}}catch(e){$('jobstate').textContent=e.message;busy=false;render()}}
$('nav').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(!b)return;tab=b.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));$('title').textContent=b.textContent;render()});
$('commands').addEventListener('click',e=>{const b=e.target.closest('[data-command]');if(b&&!busy)run(b.dataset.command)});
$('content').addEventListener('click',e=>{const b=e.target.closest('[data-bom]');if(b){bomTab=b.dataset.bom;render()}const p=e.target.closest('[data-preview]');if(p){const d=$('preview-'+p.dataset.preview);d.replaceChildren();const el=document.createElement(p.dataset.ext==='.pdf'?'iframe':'img');el.src='/artifact?id='+encodeURIComponent(p.dataset.preview);el.className='preview';el.title='Просмотр артефакта';if(el.tagName==='IMG')el.alt='Предпросмотр артефакта';d.append(el)}});
$('search').addEventListener('input',e=>{query=e.target.value.toLowerCase();render()});$('refresh').addEventListener('click',refresh);refresh();
