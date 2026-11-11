import * as model from './model.mjs';
const el=(tag,text,className)=>{const node=document.createElement(tag);if(text!=null)node.textContent=text;if(className)node.className=className;return node;};
const option=(value,label)=>{const node=el('option',label);node.value=value;return node;};
const drafts=new Map();
const event=(kind,author,body='')=>({id:crypto.randomUUID(),kind,author,body,createdAt:new Date().toISOString()});
function field(form,label,name,value='',tag='input') {
  const wrapper=el('label',label),input=el(tag);input.name=name;input.value=value;input.setAttribute('aria-label',label);wrapper.append(input);form.append(wrapper);return input;
}
export function markTarget(node,context,field) {
  node.dataset.planId=context.planId;node.dataset.roundId=context.roundId??'';node.dataset.caseId=context.caseId;
  node.dataset.observationId=context.observationId??'';node.dataset.annotationField=field;
  node.dataset.annotationAnchor=JSON.stringify([context.planId,context.roundId??'',context.caseId,context.observationId??'',field]);
  return node;
}
export function selectedTarget(root) {
  const selection=window.getSelection();
  if(!selection?.rangeCount||selection.isCollapsed)return null;
  const node=selection.anchorNode?.nodeType===Node.ELEMENT_NODE?selection.anchorNode:selection.anchorNode?.parentElement;
  const target=node?.closest('[data-annotation-field]');
  if(!target||!root.contains(target)||!target.contains(selection.focusNode))return null;
  const {planId,roundId,caseId,observationId,annotationField}=target.dataset;
  return {planId,roundId,caseId,observationId,field:annotationField,quote:selection.toString().trim()};
}
export function contextPacket(state,input,target={field:'case',quote:''}) {
  const snapshot=model.annotationContext(state,input),url=new URL(location.href);
  const params=new URLSearchParams({plan:input.planId,round:input.roundId??'',case:input.caseId,view:input.observationId?'records':'cases'});
  if(input.observationId)params.set('observation',input.observationId);
  url.hash=params.toString();
  return {kind:'test-workbench-annotation-context',planId:input.planId,roundId:input.roundId??'',caseId:input.caseId,
    observationId:input.observationId??'',url:url.href,target,context:snapshot};
}
export function renderThreads(host,{state,scope,save,message,navigate}) {
  const notes=model.annotationsFor(state,scope);
  host.append(el('h3',`批注 · ${notes.length} 条`));
  if(!notes.length)host.append(el('p','尚无批注。批注不会改变测试结果。','muted'));
  for(const note of notes) {
    const card=el('section',null,'annotation');card.id=`annotation-${note.id}`;
    const status=model.annotationStatus(note),header=el('div',null,'annotation-header');
    header.append(el('strong',`${status==='resolved'?'已处理':'待处理'} · ${note.caseId} · ${note.context.case.title}`),el('small',note.origin==='browser'?'浏览器原生批注录入':'网页批注'));
    card.append(header);
    if(note.target.quote)card.append(el('blockquote',note.target.quote,'prose'));
    card.append(el('small',`${note.context.version} / ${note.context.roundName||'方案定义'} / ${note.target.field}${note.observationId?' / 观察 '+note.observationId:''}`));
    const original=el('details');original.append(el('summary','查看批注时的原文'),el('small',`源码：${note.context.source}`),el('div',note.context.observation?[note.context.observation.notes,note.context.observation.evidence].join('\n'):[note.context.case.preconditions,note.context.case.steps,note.context.case.expected].join('\n'),'prose'));card.append(original);
    for(const item of model.orderedAnnotationEvents(note)) {
      const body=item.kind==='comment'?item.body:`${item.kind==='resolve'?'标记已处理':'重新打开'}${item.body?'：'+item.body:''}`;
      const entry=el('div',null,'annotation-entry');entry.append(el('small',`${item.author} · ${item.createdAt}`),el('div',body,'prose'));card.append(entry);
    }
    const form=el('form'),key=`reply:${note.id}`,draft=drafts.get(key)??{};
    field(form,'回复 / 处理人','author',draft.author??'').required=true;
    field(form,'回复或处理说明','body',draft.body??'','textarea');
    form.oninput=()=>drafts.set(key,Object.fromEntries(new FormData(form)));
    const reply=el('button','追加回复'),toggle=el('button',status==='resolved'?'重新打开':'标记已处理'),locate=el('button','定位此批注');
    toggle.type='submit';locate.type='button';locate.onclick=()=>navigate(note);form.append(reply,toggle,locate);
    form.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));const kind=e.submitter===toggle?(status==='resolved'?'reopen':'resolve'):'comment';save(state=>model.addAnnotationEvent(state,note.id,event(kind,data.author,data.body)),()=>drafts.delete(key));};
    card.append(form);host.append(card);
  }
}
export function renderComposer(host,options) {
  const {state,scope,save,message,navigate}=options;
  const snapshot=model.annotationContext(state,scope),key=JSON.stringify(scope),draft=drafts.get(key)??{};
  const section=el('section',null,'annotation-compose');
  section.append(el('h3',scope.observationId?'批注此执行记录':'新增批注'),el('p',`${snapshot.version} / ${snapshot.roundName||'方案定义'} / ${scope.caseId}${scope.observationId?' / 观察 '+scope.observationId:''}`,'context'));
  const form=el('form');form.className='annotation-form';
  field(form,'批注人','author',draft.author??'').required=true;
  const origin=field(form,'批注来源','origin','','select');origin.replaceChildren(option('web','网页批注'),option('browser','Codex / 浏览器原生批注录入'));origin.value=draft.origin??'web';
  const target=field(form,'批注位置','field','','select');
  const fields=scope.observationId?[['observation','此执行记录']]:[['case','整个用例'],['preconditions','前置条件'],['steps','测试步骤'],['expected','预期结果']];
  target.replaceChildren(...fields.map(([value,label])=>option(value,label)));target.value=draft.field??fields[0][0];
  const quote=field(form,'引用摘录（可选）','quote',draft.quote??'','textarea');
  const capture=el('button','引用所选文字');capture.type='button';capture.onmousedown=e=>e.preventDefault();
  capture.onclick=()=>{
    const selected=selectedTarget(document.getElementById('detail'));
    if(!selected||selected.planId!==scope.planId||selected.roundId!==(scope.roundId??'')||selected.caseId!==scope.caseId||selected.observationId!==(scope.observationId??'')) {message('请在当前目标的同一段正文内选文；批注其他执行记录请先点“批注此记录”。',true);return;}
    target.value=selected.field;quote.value=selected.quote;drafts.set(key,Object.fromEntries(new FormData(form)));message('选文已引用，保存时会核对原文。');
  };form.append(capture);
  const body=field(form,'批注内容','body',draft.body??'','textarea');body.required=true;
  form.oninput=()=>drafts.set(key,Object.fromEntries(new FormData(form)));
  const submit=el('button','保存批注','primary'),copy=el('button','复制原生批注上下文');copy.type='button';
  copy.onclick=async()=>{try{const packet=contextPacket(state,scope,{field:target.value,quote:quote.value});await navigator.clipboard.writeText(JSON.stringify(packet,null,2));message('已复制用例、轮次、原文快照与定位链接；在 Codex 原生批注中发送。');}catch(error){message(error.message,true);}};
  form.append(submit,copy);
  form.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form));save(state=>model.addAnnotation(state,{...scope,id:crypto.randomUUID(),origin:data.origin,target:{field:data.field,quote:data.quote},expectedContext:snapshot,event:event('comment',data.author,data.body)}),()=>drafts.delete(key));};
  section.append(form,el('p','Codex 原生批注：在浏览器选择正文或区域，使用宿主批注工具发送。网页提供稳定定位和上下文；聊天中的批注核对后可在此选择“原生批注录入”保存。不会自动发送聊天或回写测试结果。','muted'));
  host.append(section);renderThreads(host,{state,scope,save,message,navigate});
}
