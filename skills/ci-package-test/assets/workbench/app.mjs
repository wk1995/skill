import * as model from './model.mjs';
import {testConclusions} from './conclusions.mjs';
import {openWorkspace,read,update,initializeSource,commitSource} from './store.mjs';
import {markTarget, selectedTarget, renderComposer, renderThreads} from './annotation-ui.mjs';
import {renderFlow, renderTestLocation} from './flow-ui.mjs';
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
let pendingAction=false,queuedHash=null;
async function busy(action){
  if(pendingAction)throw new Error('正在处理上一次操作，请等待结果');pendingAction=true;document.documentElement.dataset.busy='true';
  const controls=[...document.querySelectorAll('button,input,select,textarea')].map(node=>[node,node.disabled]);for(const [node] of controls)node.disabled=true;
  try{return await action();}finally{for(const [node,disabled] of controls)if(node.isConnected)node.disabled=disabled;pendingAction=false;document.documentElement.dataset.busy='false';if(queuedHash!==null){const target=queuedHash;queuedHash=null;queueMicrotask(()=>{if(location.hash!==target)location.hash=target;else window.dispatchEvent(new HashChangeEvent('hashchange'));});}}
}
async function save(action,onSuccess=()=>{}) {
  try {return await busy(async()=>{message('正在保存，请等待主数据源确认…');state=await update(db,state.revision,action);onSuccess();if(linkError)readLocation();render();message(db.info?.mode==='github-issues'?'已核验保存到 GitHub Issues':db.info?.mode==='repository-files'?'已保存到仓库工作区 · 尚未提交 Git':'已保存至浏览器预览 · 尚未同步主数据源');return true;}); }
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
  renderSource();
  $('flow').replaceChildren();
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
  renderConclusion(round);
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
  renderFlow($('flow'),{context:round??plan,caseId:definitions.some(item=>item.id===caseId)?caseId:'',environmentId,labels,
    navigate:id=>{linkError='';caseId=id;observationTarget='';annotationId='';view='cases';$('search').value='';$('type').value='';$('status').value='';render();},
    selectEnvironment:id=>{environmentId=id;render();}});
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
  if(round) for(const reason of item.selectionReasons??[]) detail.append(pill(({'previous-failure':'失败复测',smoke:'每轮冒烟',change:'变更纳入',unfinished:'上轮未完成','conditional-next':'条件分支纳入',dependency:'前置依赖纳入'})[reason]??reason));
  for(const [label,value,field] of [['前置条件',item.preconditions,'preconditions'],['测试步骤',item.steps,'steps'],['预期结果',item.expected,'expected']]) detail.append(el('h3',label),markTarget(el('div',value||'','prose'),caseScope,field));
  const locationEnv=round?.environments.find(env=>env.id===environmentId);
  const locationExecution=locationEnv&&round.workflow?model.inspectWorkflow(round).executions.find(entry=>entry.caseId===item.id&&entry.environmentId===locationEnv.id):null;
  renderTestLocation(detail,item,{version:round?.version??plan.version,source:round?.source??plan.source,build:round?.build??plan.build,planId,roundId,environmentId:locationEnv?.id??'',environment:locationEnv,...locationExecution,state:locationExecution?.state??(round?'未选择状态机环境':'定义')},message);
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
  field(form,'前置用例 ID（逗号分隔）','dependsOn',(item.dependsOn??[]).join(', '));
  field(form,'结果分支 next（JSON，可留空）','next',item.next?JSON.stringify(item.next,null,2):'','textarea');
  field(form,'测试定位 testLocation（JSON，可留空）','testLocation',item.testLocation?JSON.stringify(item.testLocation,null,2):'','textarea');
  form.append(el('button','保存定义（不改历史轮次）','primary'));
  form.onsubmit=event=>{event.preventDefault();try{const data=new FormData(form),edited={...item,title:data.get('title'),preconditions:data.get('preconditions'),steps:data.get('steps'),expected:data.get('expected'),types:data.getAll('types')};
    edited.dependsOn=data.get('dependsOn').split(',').map(id=>id.trim()).filter(Boolean);
    if(data.get('next').trim())edited.next=JSON.parse(data.get('next'));else delete edited.next;
    if(data.get('testLocation').trim())edited.testLocation=JSON.parse(data.get('testLocation'));else delete edited.testLocation;
    save(state=>model.editCase(state,plan.id,edited));}catch(error){message(error.message,true);}};
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
    const readiness=env?model.inspectWorkflow(round).executions.find(entry=>entry.caseId===item.id&&entry.environmentId===env.id):null;
    const current=readiness?.state??'untested';
    if(readiness?.unmetDependencies.length)detail.append(el('p',`前置依赖未满足：${readiness.unmetDependencies.map(dep=>`${dep.caseId}（${labels[dep.state]}${dep.dependencyStale?'，结果已过期':''}）`).join('、')}。需在本轮、本环境通过。`,'context'));
    if(readiness?.dependencyStale)detail.append(el('p','前置用例的执行证据已变化；历史结果保留，当前用例需要重新验证。','context'));
    detail.append(el('p',env?`当前环境执行状态：${labels[current]}。通过/失败/部分执行前须开始；待测可直接阻塞或跳过，保留历史。`:'请选择环境查看执行状态。','context'));
    const begin=el('button',current==='untested'?'开始此用例':'重新执行此用例');begin.type='button';begin.id='start-execution';begin.disabled=!active||!env||current==='running'||!readiness?.dependenciesSatisfied;
    begin.onclick=()=>{const tester=form.elements.tester.value;save(state=>model.startExecution(state,round.id,{id:uuid(),from:current,actor:tester,at:now(),caseId:item.id,environmentId:env.id}));};form.append(begin);
  }
  const meanings=el('details');meanings.append(el('summary','如何区分失败、部分执行、阻塞和跳过'));
  for(const [status,description] of Object.entries(model.CONTRACT.routing.semantics))meanings.append(el('p',`${labels[status]}：${({passed:'本次要求的检查均符合预期。',failed:'已观察到实际行为不符合预期；其他检查通过不能掩盖失败。',partial:'只执行或验证了一部分；说明已完成及未验证内容。已发现问题应选失败。',blocked:'缺少账号、环境或外部依赖等前置条件，无法执行或继续。',skipped:'明确决定本轮不执行，填写范围或优先级原因；不计为通过。'})[status]??description}`,'context'));detail.append(meanings);
  const status=field(form,'结果','status','','select'); status.replaceChildren(...(managed?model.RESULTS:model.STATUSES.filter(status=>status!=='running')).map(value=>option(value,labels[value])));status.value=draft.status??'passed';
  const time=field(form,'执行时间（本地时区）','executedAt',draft.executedAt??localTime());time.type='datetime-local';
  const timeRequirement=()=>{time.required=!(managed&&['blocked','skipped'].includes(status.value));};status.addEventListener('change',timeRequirement);timeRequirement();
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
    const observations=ids.map(id=>({id:uuid(),caseId:id,environmentId:bound.environmentId,environment:structuredClone(env),status:data.status,executedAt:managed&&model.executionState(round,id,bound.environmentId)==='untested'&&['blocked','skipped'].includes(data.status)?null:data.executedAt?new Date(data.executedAt).toISOString():null,recordedAt:now(),tester:data.tester,notes:data.notes,evidence:data.evidence}));
    save(state=>model.recordBatch(state,bound.roundId,observations)).then(()=>{if(!$('message').classList.contains('error')){drafts.delete(bound.key);render();}});
  };detail.append(form);
  if(env&&managed)renderNextTest(detail,round,item,env);
  detail.append(el('h3','执行历史 · 逐条保留'));
  for(const record of round.observations.filter(record=>record.caseId===item.id).reverse()) renderObservation(detail,record);
}
function renderNextTest(detail,round,item,env) {
  const advice=model.nextTest(round,item.id,env.id),panel=el('section');panel.id='next-test';
  panel.append(el('h3','下一步测什么'));
  const actionLabels={current:'继续当前用例',test:'执行后续用例',retry:'重新验证当前用例',wait:'等待条件恢复',done:'此分支结束',unconfigured:'尚未配置下一步',unavailable:'当前流程不支持分支',prerequisite:'先完成前置用例',stale:'依赖已变化，先记录阻塞'};
  panel.append(el('strong',actionLabels[advice.action]),el('p',({current:'请先执行或继续当前用例，再根据实际结果选择后续测试。',unconfigured:'该用例尚未配置结果分支，请完善定义，不能自动猜测下一项。',unavailable:'旧流程请准备新轮次后使用按环境分支。',prerequisite:'请先在本轮、本环境完成下方前置用例，再返回目标测试。',stale:'执行期间依赖证据已变化；请记录阻塞，确认前置条件后重新开始。'})[advice.action]??advice.reason,'context'));
  if(advice.resumeWhen)panel.append(el('p',`恢复条件：${advice.resumeWhen}`,'context'));
  if(advice.unresolvedFailureId)panel.append(el('p',`仍有未解决失败：${advice.unresolvedFailureId}。部分执行、阻塞或跳过均不会清除此失败；需在本环境重测通过。`,'error'));
  if(advice.basedOnObservationId)panel.append(el('small',`依据：${labels[advice.state]} · ${advice.basedOnObservationId} · ${env.label}`));
  if(advice.target) {
    panel.append(el('p',`${advice.target.id} · ${advice.target.title}`));
    for(const [label,value] of [['前置条件',advice.target.preconditions],['步骤',advice.target.steps],['预期',advice.target.expected]])panel.append(el('p',`${label}：${value}`,'prose'));
    if(advice.action!=='current') {
      const button=el('button',`打开 ${advice.target.id}`);button.type='button';button.disabled=!advice.available;
      button.onclick=()=>{linkError='';caseId=advice.targetCaseId;observationTarget='';annotationId='';view='cases';$('search').value='';$('type').value='';$('status').value='';render();};panel.append(button);
      panel.append(el('small',`目标当前状态：${labels[advice.targetState]}。打开用例不会自动执行或修改结果。`));
    }
  }
  detail.append(panel);
}
function renderObservation(detail,record) {
  const card=el('div',null,'record'),scope={planId,roundId,caseId:record.caseId,observationId:record.id};card.id=`observation-${record.id}`;
  card.dataset.caseId=record.caseId;card.dataset.observationId=record.id;
  card.append(el('strong',`${record.caseId} · ${labels[record.status]} · ${record.environment.label} · ${record.tester}`),el('small',`执行：${record.executedAt??'未执行'} / 记录：${record.recordedAt}`),el('small',record.environment.configuration),markTarget(el('p',record.notes,'prose'),scope,'observation'),markTarget(el('div',record.evidence,'prose'),scope,'observation'));
  const annotate=el('button','批注此记录');annotate.type='button';annotate.onclick=()=>{caseId=record.caseId;observationTarget=record.id;annotationId='';view='cases';$('search').value='';$('type').value='';$('status').value='';render();document.querySelector('.annotation-compose')?.scrollIntoView({block:'center'});};card.append(annotate);detail.append(card);
}
for(const mode of ['cases','records','annotations']) $(`${mode}-view`).onclick=()=>{view=mode;render();};
document.addEventListener('selectionchange',()=>{
  const selected=selectedTarget($('detail'));if(!selected||selected.planId!==planId||selected.roundId!==roundId)return;
  caseId=selected.caseId;observationTarget=selected.observationId;annotationId='';syncLocation(selected.field);
});
$('copy-results').onclick=async()=>{const round=state.rounds.find(item=>item.id===roundId);if(!round){message('请选择执行轮次。',true);return;}const report=[`${round.version} / ${round.name}\nSource: ${round.source}\nCI: ${round.build}`, ...round.cases.map(item=>`${item.id} ${item.title}: ${labels[model.statusOf(round,item.id)]}`), ...round.observations.map(item=>`${item.caseId} · ${item.environment.label} · ${item.executedAt??'未执行'} · ${labels[item.status]}\n${item.notes}\n${item.evidence}`)].join('\n');try{await navigator.clipboard.writeText(report);message('本轮结果已复制');}catch{message('剪贴板不可用，请导出 JSON 归档。',true);}};
for(const [id,items] of [['type',model.TYPES],['status',model.STATUSES]]) select(id,[['','全部'+(id==='type'?'类型':'结果')],...items.map(value=>[value,labels[value]])],'');
for(const id of ['search','type','status']) $(id).addEventListener('input',render);
$('version').onchange=()=>{linkError='';planId=state.plans.find(plan=>plan.version===$('version').value)?.id??'';roundId='';render();};
$('plan').onchange=()=>{linkError='';planId=$('plan').value;roundId='';render();};$('round').onchange=()=>{linkError='';roundId=$('round').value;render();};
$('import-button').onclick=()=>$('import').click();
$('import').onchange=async event=>{try{if(!event.target.files.length)return;const value=JSON.parse(await event.target.files[0].text());await save(state=>value.schemaVersion?model.importArchive(state,value):model.importPlan(state,value));}catch(error){message(error.message,true);}finally{event.target.value='';}};
$('json-form').onsubmit=async event=>{event.preventDefault();try{const value=JSON.parse(new FormData(event.target).get('json'));await save(state=>value.schemaVersion?model.importArchive(state,value):model.importPlan(state,value));}catch(error){message(error.message,true);}};
$('export').onclick=()=>download(state,'test-workbench-archive.json');
$('export-ai').onclick=()=>{try{download(model.exportAI(state),'test-workbench-ai-state.json');message('AI 快照包含状态机契约、原始归档、当前状态及允许的下一步；恢复数据请使用归档。');}catch(error){message(error.message,true);}};
$('reload').onclick=async()=>{try{await busy(async()=>{state=await read(db);if(linkError)readLocation();render();message('已读取最新数据；未保存的草稿保留。');});}catch(error){message(error.message,true);}};
$('round-form').onsubmit=event=>{event.preventDefault();const data=new FormData(event.target),id=uuid(),targetPlanId=planId,changed=data.get('changed').trim();save(state=>model.createRound(state,{id,name:data.get('name'),planId:targetPlanId,createdAt:now(),changedIds:changed?changed.split(',').map(value=>value.trim()).filter(Boolean):undefined,includeUnfinished:data.has('unfinished')})).then(()=>{if(!$('message').classList.contains('error')){roundId=id;render();}});};
$('environment-form').onsubmit=event=>{event.preventDefault();const data=Object.fromEntries(new FormData(event.target)),id=uuid();save(state=>model.registerEnvironment(state,{id,...data})).then(()=>{if(!$('message').classList.contains('error')){environmentId=id;render();}});};
window.addEventListener('hashchange',async()=>{if(pendingAction){queuedHash=location.hash;return;}if(!db)return;try{await busy(async()=>{state=await read(db);readLocation();$('search').value='';$('type').value='';$('status').value='';render();});}catch(error){message(error.message,true);}});
try {db=await openWorkspace();state=await read(db);readLocation();render(); } catch(error) {message(`无法载入数据：${error.message}。请保留原数据库并导出可用备份，不要清空。`,true);}

function renderSource(){
  const info=db?.info??{},local=info.mode==='local-preview';
  $('source-status').textContent=local?'浏览器预览 / 旧数据 · 尚未连接主数据源':`${info.mode==='repository-files'?'仓库文件':'GitHub Issues（默认）'} · ${info.repository??''}${info.path?' / '+info.path:''}${info.actor?' · '+info.actor:''} · ${!info.initialized?'等待初始化':info.mode==='github-issues'?'已连接':info.dirty?'工作区有未提交数据':'数据已入库'}${info.head?' · '+info.head.slice(0,8):''}`;
  $('initialize-source').hidden=local||Boolean(info.initialized);$('commit-source').hidden=info.mode!=='repository-files';$('commit-source').disabled=!info.initialized||!info.dirty||!info.branch;
  const link=$('source-link');link.hidden=!info.url;if(info.url){link.href=info.url;link.textContent='打开工作台 Issue';}
}
$('initialize-source').onclick=async()=>{try{await busy(async()=>{state=await initializeSource(db);readLocation();render();message('主数据源已初始化；后续保存将写入此目标。');});}catch(error){message(error.message,true);}};
$('commit-source').onclick=async()=>{try{await busy(async()=>{message('正在提交测试数据…');state=await commitSource(db,state.revision);render();message('当前测试数据已提交 Git；其他文件未纳入此次提交。');});}catch(error){message(error.message,true);}};

function renderConclusion(round){
 const panel=$('test-conclusion');panel.replaceChildren();if(!round)return;
 const report=testConclusions(state).rounds.find(item=>item.roundId===round.id),names={passed:'通过',failed:'未通过',blocked:'阻塞',partial:'部分执行',incomplete:'尚未完成',legacy:'旧流程，未推断结论'};
 panel.append(el('h2',`本轮测试结论：${names[report.verdict]}`),el('p',`${round.version} / ${round.name} · ${round.source}`,'context'));
 panel.append(el('p','根据本轮、各环境的实际记录计算。结论与执行记录一同保存；文件模式需提交后才算入库。结论不代表发布批准。','muted'));
 if(report.counts)panel.append(el('p',Object.entries(report.counts).map(([status,count])=>`${labels[status]} ${count}`).join(' · ')));
 for(const item of report.executions.filter(item=>item.result!=='passed'))panel.append(el('p',`${item.caseId} / ${round.environments.find(env=>env.id===item.environmentId)?.label??item.environmentId}：${labels[item.result]}${item.unresolvedFailureId?' · 未解决失败 '+item.unresolvedFailureId:''}${item.dependencyStale?' · 前置证据已过期':''}`,'muted'));
}
