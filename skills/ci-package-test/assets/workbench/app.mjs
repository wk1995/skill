import * as model from './model.mjs';
import {openStore, read, update} from './store.mjs';
import {markTarget, selectedTarget, renderComposer, renderThreads} from './annotation-ui.mjs';
const $ = id => document.getElementById(id);
const labels = {smoke:'冒烟',functional:'功能',performance:'性能',compatibility:'兼容性',stability:'稳定性',security:'安全',usability:'易用性','install-upgrade':'安装升级',integration:'集成',passed:'通过',failed:'失败',partial:'部分执行',blocked:'阻塞',untested:'待测',running:'测试中',skipped:'跳过',draft:'草稿',ready:'就绪',completed:'已结束',prepare:'标记就绪',begin:'开始本轮',complete:'结束本轮',reopen:'重新打开'};
const el = (tag, text, className) => { const node = document.createElement(tag); if (text != null) node.textContent = text; if (className) node.className = className; return node; };
const option = (value, text) => { const node = el('option', text); node.value = value; return node; };
const uuid = () => crypto.randomUUID();
const now = () => new Date().toISOString();
const localTime = () => { const date = new Date(); return new Date(date - date.getTimezoneOffset()*60000).toISOString().slice(0,16); };
const hash = new URLSearchParams(location.hash.slice(1));
let state = model.empty(), db, planId = hash.get('plan') ?? '', roundId = hash.get('round') ?? '', caseId = hash.get('case') ?? '', environmentId = '', view=['records','annotations'].includes(hash.get('view'))?hash.get('view'):'cases', observationTarget=hash.get('observation')??'', annotationId=hash.get('annotation')??'';
let linkError='';
const selections=new Map();
const drafts = new Map();
const draftKey = () => JSON.stringify([roundId,caseId,environmentId]);
function message(text, error=false) { $('message').textContent=text; $('message').className=error?'error':''; }
function download(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  const anchor=el('a'); anchor.href=url; anchor.download=name; anchor.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function save(action,onSuccess=()=>{}) {
  try { state=await update(db,state.revision,action);onSuccess();if(linkError)readLocation();render();message('已保存 · 历史记录保留');return true; }
  catch(error) { message(error.message,true);return false; }
}
function syncLocation(field='') {
  if(linkError)return;
  const params=new URLSearchParams({plan:planId,round:roundId,case:caseId,view});
  if(observationTarget)params.set('observation',observationTarget);if(annotationId)params.set('annotation',annotationId);if(field)params.set('field',field);
  history.replaceState(null,'',`#${params}`);
}
function readLocation() {
  const params=new URLSearchParams(location.hash.slice(1));
  planId=params.get('plan')??'';roundId=params.get('round')??'';caseId=params.get('case')??'';observationTarget=params.get('observation')??'';annotationId=params.get('annotation')??'';
  view=['records','annotations'].includes(params.get('view'))?params.get('view'):'cases';linkError='';
  const plan=state.plans.find(item=>item.id===planId),round=state.rounds.find(item=>item.id===roundId),note=(state.annotations??[]).find(item=>item.id===annotationId);
  if(planId&&!plan)linkError='链接中的方案不存在；请先导入对应归档或明确选择目标方案。';
  else if(roundId&&(!round||round.planId!==planId))linkError='链接中的轮次不属于此方案，请核对批注上下文。';
  else if(annotationId&&(!note||note.planId!==planId||note.roundId!==roundId||note.caseId!==caseId))linkError='链接中的批注与用例上下文不一致。';
  else if(caseId&&!(round?.cases??plan?.cases??[]).some(item=>item.id===caseId)&&!note)linkError='链接中的用例不存在，不能自动改为其他用例。';
  else if(observationTarget&&!round?.observations.some(item=>item.id===observationTarget&&item.caseId===caseId))linkError='链接中的执行记录与用例不一致。';
  if(note&&!linkError){observationTarget=note.observationId;if(!(round?.cases??plan?.cases??[]).some(item=>item.id===caseId))view='annotations';}
}
function navigateAnnotation(note) {
  linkError='';
  planId=note.planId;roundId=note.roundId;caseId=note.caseId;observationTarget=note.observationId;annotationId=note.id;
  const definitions=roundId?state.rounds.find(round=>round.id===roundId)?.cases:state.plans.find(plan=>plan.id===planId)?.cases;
  view=definitions?.some(item=>item.id===caseId)?'cases':'annotations';
  $('search').value='';$('type').value='';$('status').value='';render();document.getElementById(`annotation-${note.id}`)?.scrollIntoView({block:'center'});
}
function select(id, items, selected) { $(id).replaceChildren(...items.map(([value,label])=>option(value,label))); $(id).value=selected; }
const pill=(text,type)=>el('span',text,`pill ${type??''}`);
function render() {
  const versions=[...new Set(state.plans.map(plan=>plan.version))];
  let plan=state.plans.find(plan=>plan.id===planId)??state.plans[0]; planId=plan?.id??'';
  select('version',versions.map(value=>[value,value]),plan?.version??'');
  select('plan',state.plans.filter(item=>item.version===plan?.version).map(item=>[item.id,item.title]),planId);
  let round=state.rounds.find(item=>item.id===roundId&&item.planId===planId); roundId=round?.id??'';
  select('round',[['','方案定义'],...model.roundsFor(state,planId).map(item=>[item.id,item.name])],roundId);
  const definitions=round?.cases??plan?.cases??[];
  $('identity').replaceChildren();
  if(plan) for(const [label,value] of [['源码',round?.source??plan.source],['CI / 产物',round?.build??plan.build],['PR / 变更',round?.pr??plan.pr]]) {
    const p=el('p',`${label}：`);
    if(/^https?:\/\//i.test(value)) {const a=el('a',value);a.href=value;a.target='_blank';a.rel='noopener noreferrer';p.append(a);} else p.append(document.createTextNode(value||'未提供'));
    $('identity').append(p);
  }
  renderWorkflow(round);
  const counts=Object.fromEntries(model.STATUSES.map(status=>[status,definitions.filter(item=>(round?model.statusOf(round,item.id):'untested')===status).length]));
  $('stats').replaceChildren(...[['用例总数',definitions.length],...model.STATUSES.map(status=>[labels[status],counts[status]])].map(([label,count])=>{const div=el('div',null,'stat');div.append(el('strong',count),el('span',label));return div;}));
  const query=$('search').value.toLowerCase();
  const shown=definitions.filter(item=>(`${item.id} ${item.title}`).toLowerCase().includes(query)&&(!$('type').value||item.types.includes($('type').value))&&(!$('status').value||(round?model.statusOf(round,item.id):'untested')===$('status').value));
  if(!shown.some(item=>item.id===caseId)&&view!=='annotations') caseId=shown[0]?.id??'';
  const selected=selections.get(roundId)??new Set();selections.set(roundId,selected);
  $('case-list').replaceChildren(...shown.map(item=>{
    const wrapper=el('div',null,'case-row');
    if(round){const check=el('input');check.type='checkbox';check.checked=selected.has(item.id);check.setAttribute('aria-label',`批量选择 ${item.id}`);check.onchange=()=>{check.checked?selected.add(item.id):selected.delete(item.id);};wrapper.append(check);}
    const button=el('button',null,item.id===caseId?'selected':''); button.append(el('span',`${item.id} · ${item.priority}`,'case-id'),el('span',item.title));
    for(const type of item.types) button.append(pill(labels[type],type));
    const status=round?model.statusOf(round,item.id):'untested';button.append(pill(labels[status],status));
    button.onclick=()=>{linkError='';caseId=item.id;view='cases';observationTarget='';annotationId='';render();};wrapper.append(button);return wrapper;
  }));
  const detail=$('detail');detail.replaceChildren();
  if(linkError){detail.append(el('h2','无法定位批注上下文'),el('p',linkError,'context'));return;}
  if(!round?.observations.some(item=>item.id===observationTarget&&item.caseId===caseId))observationTarget='';
  const scoped={planId,roundId};
  if(!(state.annotations??[]).some(note=>note.id===annotationId&&note.planId===planId&&note.roundId===roundId&&note.caseId===caseId))annotationId='';
  syncLocation();
  if(view==='annotations') {
    detail.append(el('h2','批注'),el('p','网页批注可回复、标记处理或重新打开；原生批注通过稳定定位与原文快照联调。','context'));
    renderThreads(detail,{state,scope:scoped,save,message,navigate:navigateAnnotation});return;
  }
  if(view==='records') {
    detail.append(el('h2','执行记录'),el('p',round?'本轮所有观察逐条保留；切换轮次可查看历史。':'请选择一个执行轮次。','context'));
    if(round) for(const observation of [...round.observations].reverse()) renderObservation(detail,observation);
    return;
  }
  const item=definitions.find(item=>item.id===caseId);
  if(!item) {detail.append(el('p',plan?'没有匹配的用例。':'导入测试方案开始。一个工作台持续管理所有版本、方案和测试轮次。','empty'));return;}
  const caseScope={planId,roundId,caseId:item.id};
  detail.dataset.planId=planId;detail.dataset.roundId=roundId;detail.dataset.caseId=item.id;
  detail.append(el('span',`${item.id} · ${round?.name??'当前方案定义'}`,'eyebrow'),markTarget(el('h2',item.title),caseScope,'case'));
  for(const type of item.types) detail.append(pill(labels[type],type));
  if(round) for(const reason of item.selectionReasons??[]) detail.append(pill(({'previous-failure':'失败复测',smoke:'每轮冒烟',change:'变更纳入',unfinished:'上轮未完成'})[reason]??reason));
  for(const [label,value,field] of [['前置条件',item.preconditions,'preconditions'],['测试步骤',item.steps,'steps'],['预期结果',item.expected,'expected']]) detail.append(el('h3',label),markTarget(el('div',value||'','prose'),caseScope,field));
  const link=el('button','复制用例定位信息'); link.onclick=async()=>{try {await navigator.clipboard.writeText(`${plan.version} / ${plan.title} / ${round?.name??'方案定义'} / ${caseId}\n${location.href}`);message('定位信息已复制');}catch{message(location.href);}};detail.append(link);
  if(!round) renderEditor(detail,plan,item); else renderExecution(detail,round,item);
  renderComposer(detail,{state,scope:{...caseScope,observationId:observationTarget},save,message,navigate:navigateAnnotation});
}
function field(form,label,name,value='',tag='input') {
  const wrapper=el('label',label),input=el(tag);input.name=name;input.value=value;input.setAttribute('aria-label',label);wrapper.append(input);form.append(wrapper);return input;
}
function renderEditor(detail,plan,item) {
  const panel=el('details');panel.append(el('summary','编辑当前用例定义与分类'));
  const form=el('form',null,'editor');
  field(form,'标题','title',item.title).required=true;
  const types=el('div'); for(const type of model.TYPES) {const label=el('label',labels[type],'check'),input=el('input');input.type='checkbox';input.name='types';input.value=type;input.checked=item.types.includes(type);label.prepend(input);types.append(label);}form.append(types);
  field(form,'前置条件','preconditions',item.preconditions,'textarea');field(form,'步骤','steps',item.steps,'textarea').required=true;field(form,'预期','expected',item.expected,'textarea').required=true;
  form.append(el('button','保存定义（不改历史轮次）','primary'));
  form.onsubmit=event=>{event.preventDefault();const data=new FormData(form);save(state=>model.editCase(state,plan.id,{...item,title:data.get('title'),preconditions:data.get('preconditions'),steps:data.get('steps'),expected:data.get('expected'),types:data.getAll('types')}));};
  panel.append(form);detail.append(panel);
}
function renderWorkflow(round) {
  const panel=$('workflow');panel.replaceChildren();
  if(!round)return;
  if(!round.workflow){panel.append(el('p','旧流程：保留原始结果，未补造开始或轮次事件。新建下一轮可启用状态机。','context'));return;}
  const current=model.inspectWorkflow(round);
  panel.append(el('h3',`轮次状态：${labels[current.state]}`));
  const form=el('form');form.id='workflow-form';
  field(form,'操作人','actor').required=true;field(form,'原因（重新打开必填）','reason');
  for(const action of model.roundActions(round)) {
    const button=el('button',labels[action.action]);button.value=action.action;button.disabled=!action.allowed;
    if(!action.allowed)button.title=action.missing.includes('attached-environment')?'请先加入登记环境':'仍有待测或测试中的执行';
    form.append(button);
  }
  form.onsubmit=event=>{event.preventDefault();if(!event.submitter)return;const data=new FormData(form);save(state=>model.transitionRound(state,round.id,{id:uuid(),action:event.submitter.value,from:current.state,actor:data.get('actor'),at:now(),reason:data.get('reason')}));};
  panel.append(form,el('small','结束代表记录已完成，失败、阻塞和跳过仍会保留。'));
  const history=el('details');history.append(el('summary',`状态事件 · ${round.workflow.events.length}`));
  for(const event of round.workflow.events)history.append(el('p',`${event.scope==='round'?'轮次':`${event.caseId} / ${event.environmentId}`} · ${event.from} → ${event.to} · ${event.actor} · ${event.at}${event.reason?` · ${event.reason}`:''}`,'context'));
  panel.append(history);
}
function renderExecution(detail,round,item) {
  detail.append(el('h3','本轮环境 / 设备'));
  const row=el('div',null,'row'),label=el('label','选择已登记环境'),choice=el('select');choice.id='environment';choice.setAttribute('aria-label','选择已登记环境');choice.append(option('','请选择'),...state.environments.map(env=>option(env.id,`${env.label} · ${env.kind}`)));choice.value=environmentId;environmentId=choice.value;
  choice.onchange=()=>{environmentId=choice.value;render();};label.append(choice);row.append(label);
  const attach=el('button','加入本轮');attach.type='button';attach.onclick=()=>save(state=>model.attachEnvironment(state,round.id,environmentId));row.append(attach);detail.append(row);
  const env=round.environments.find(env=>env.id===environmentId);
  detail.append(el('p',env?`${env.label} · ${env.configuration}`:'保存前须登记环境，并加入本轮。','context'));
  const form=el('form');form.id='observation-form';const draft=drafts.get(draftKey())??{};
  const managed=Boolean(round.workflow),active=managed?model.inspectWorkflow(round).state==='running':true;
  if(managed) {
    const current=env?model.executionState(round,item.id,env.id):'untested';
    detail.append(el('p',env?`当前环境执行状态：${labels[current]}。保存结果前须开始执行；重测会保留旧记录。`:'请选择环境查看执行状态。','context'));
    const begin=el('button',current==='untested'?'开始此用例':'重新执行此用例');begin.type='button';begin.id='start-execution';begin.disabled=!active||!env||current==='running';
    begin.onclick=()=>{const tester=form.elements.tester.value;save(state=>model.startExecution(state,round.id,{id:uuid(),from:current,actor:tester,at:now(),caseId:item.id,environmentId:env.id}));};form.append(begin);
  }
  const status=field(form,'结果','status','','select'); status.replaceChildren(...(managed?model.RESULTS:model.STATUSES.filter(status=>status!=='running')).map(value=>option(value,labels[value])));status.value=draft.status??'passed';
  const time=field(form,'执行时间（本地时区）','executedAt',draft.executedAt??localTime());time.type='datetime-local';time.required=true;
  field(form,'执行人','tester',draft.tester??'').required=true;field(form,'备注 / 缺陷','notes',draft.notes??'','textarea');field(form,'证据路径或链接','evidence',draft.evidence??'','textarea');
  form.oninput=()=>drafts.set(draftKey(),Object.fromEntries(new FormData(form)));
  const single=el('button','新增执行记录','primary');single.disabled=!active;form.append(single);
  const batch=el('button','批量记录到所选用例');batch.type='submit';batch.value='batch';batch.disabled=!active;form.append(batch);
  if(managed){const startBatch=el('button','开始所选用例');startBatch.type='button';startBatch.id='start-batch';startBatch.disabled=!active||!env;startBatch.onclick=()=>{const actor=form.elements.tester.value;save(state=>model.startExecutionBatch(state,round.id,[...(selections.get(round.id)??[])].map(id=>({id:uuid(),from:model.executionState(round,id,env.id),actor,at:now(),caseId:id,environmentId:env.id}))));};form.append(startBatch);}
  const bound={roundId:round.id,caseId:item.id,environmentId,key:draftKey()};
  form.onsubmit=event=>{
    event.preventDefault();const data=Object.fromEntries(new FormData(form));
    if(!env) {message('请选择已加入本轮的登记环境。',true);return;}
    const ids=event.submitter===batch?[...(selections.get(bound.roundId)??[])]:[bound.caseId];
    const observations=ids.map(id=>({id:uuid(),caseId:id,environmentId:bound.environmentId,environment:structuredClone(env),status:data.status,executedAt:new Date(data.executedAt).toISOString(),recordedAt:now(),tester:data.tester,notes:data.notes,evidence:data.evidence}));
    save(state=>model.recordBatch(state,bound.roundId,observations)).then(()=>{if(!$('message').classList.contains('error')){drafts.delete(bound.key);render();}});
  };detail.append(form,el('h3','执行历史 · 逐条保留'));
  for(const record of round.observations.filter(record=>record.caseId===item.id).reverse()) renderObservation(detail,record);
}
function renderObservation(detail,record) {
  const card=el('div',null,'record'),scope={planId,roundId,caseId:record.caseId,observationId:record.id};card.id=`observation-${record.id}`;
  card.dataset.caseId=record.caseId;card.dataset.observationId=record.id;
  card.append(el('strong',`${record.caseId} · ${labels[record.status]} · ${record.environment.label} · ${record.tester}`),el('small',`执行：${record.executedAt} / 记录：${record.recordedAt}`),el('small',record.environment.configuration),markTarget(el('p',record.notes,'prose'),scope,'observation'),markTarget(el('div',record.evidence,'prose'),scope,'observation'));
  const annotate=el('button','批注此记录');annotate.type='button';annotate.onclick=()=>{caseId=record.caseId;observationTarget=record.id;annotationId='';view='cases';$('search').value='';$('type').value='';$('status').value='';render();document.querySelector('.annotation-compose')?.scrollIntoView({block:'center'});};card.append(annotate);detail.append(card);
}
for(const mode of ['cases','records','annotations']) $(`${mode}-view`).onclick=()=>{view=mode;render();};
document.addEventListener('selectionchange',()=>{
  const selected=selectedTarget($('detail'));if(!selected||selected.planId!==planId||selected.roundId!==roundId)return;
  caseId=selected.caseId;observationTarget=selected.observationId;annotationId='';syncLocation(selected.field);
});
$('copy-results').onclick=async()=>{const round=state.rounds.find(item=>item.id===roundId);if(!round){message('请选择执行轮次。',true);return;}const report=[`${round.version} / ${round.name}\nSource: ${round.source}\nCI: ${round.build}`, ...round.cases.map(item=>`${item.id} ${item.title}: ${labels[model.statusOf(round,item.id)]}`), ...round.observations.map(item=>`${item.caseId} · ${item.environment.label} · ${item.executedAt} · ${labels[item.status]}\n${item.notes}\n${item.evidence}`)].join('\n');try{await navigator.clipboard.writeText(report);message('本轮结果已复制');}catch{message('剪贴板不可用，请导出 JSON 归档。',true);}};
for(const [id,items] of [['type',model.TYPES],['status',model.STATUSES]]) select(id,[['','全部'+(id==='type'?'类型':'结果')],...items.map(value=>[value,labels[value]])],'');
for(const id of ['search','type','status']) $(id).addEventListener('input',render);
$('version').onchange=()=>{linkError='';planId=state.plans.find(plan=>plan.version===$('version').value)?.id??'';roundId='';render();};
$('plan').onchange=()=>{linkError='';planId=$('plan').value;roundId='';render();};$('round').onchange=()=>{linkError='';roundId=$('round').value;render();};
$('import-button').onclick=()=>$('import').click();
$('import').onchange=async event=>{try{if(!event.target.files.length)return;const value=JSON.parse(await event.target.files[0].text());await save(state=>value.schemaVersion?model.importArchive(state,value):model.importPlan(state,value));}catch(error){message(error.message,true);}finally{event.target.value='';}};
$('json-form').onsubmit=async event=>{event.preventDefault();try{const value=JSON.parse(new FormData(event.target).get('json'));await save(state=>value.schemaVersion?model.importArchive(state,value):model.importPlan(state,value));}catch(error){message(error.message,true);}};
$('export').onclick=()=>download(state,'test-workbench-archive.json');
$('export-ai').onclick=()=>{try{download(model.exportAI(state),'test-workbench-ai-state.json');message('AI 快照包含状态机契约、原始归档、当前状态及允许的下一步；恢复数据请使用归档。');}catch(error){message(error.message,true);}};
$('reload').onclick=async()=>{try{state=await read(db);if(linkError)readLocation();render();message('已读取最新数据；未保存的草稿保留。');}catch(error){message(error.message,true);}};
$('round-form').onsubmit=event=>{event.preventDefault();const data=new FormData(event.target),id=uuid(),changed=data.get('changed').trim();save(state=>model.createRound(state,{id,name:data.get('name'),planId,createdAt:now(),changedIds:changed?changed.split(',').map(value=>value.trim()).filter(Boolean):undefined,includeUnfinished:data.has('unfinished')})).then(()=>{if(!$('message').classList.contains('error')){roundId=id;render();}});};
$('environment-form').onsubmit=event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target)),id=uuid();save(state=>model.registerEnvironment(state,{id,...data})).then(()=>{if(!$('message').classList.contains('error')){environmentId=id;render();}});};
window.addEventListener('hashchange',async()=>{if(!db)return;try{state=await read(db);readLocation();$('search').value='';$('type').value='';$('status').value='';render();}catch(error){message(error.message,true);}});
try { const workspace=new URLSearchParams(location.search).get('workspace');db=await openStore(workspace?`ci-package-test-workbench:${workspace}`:undefined);state=await read(db);readLocation();render(); } catch(error) {message(`无法载入数据：${error.message}。请保留原数据库并导出可用备份，不要清空。`,true);}
