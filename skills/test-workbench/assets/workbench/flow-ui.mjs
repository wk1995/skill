import {projectFlow} from './flow.mjs';
import {locationHint,formatTestLocation} from './test-location.mjs';
const el=(tag,text,className)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
const svg=(tag,attributes)=>{const node=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,value);return node;};
const actions={current:'继续当前用例',test:'执行后续用例',retry:'重新验证当前用例',wait:'等待条件恢复',done:'此分支结束',unconfigured:'尚未配置下一步',prerequisite:'先完成前置用例',stale:'依赖已变化，先记录阻塞'};
export function renderFlow(container,{context,caseId,environmentId,labels,navigate,selectEnvironment}) {
  container.replaceChildren();if(!context)return;
  const flow=projectFlow(context,{caseId,environmentId});
  const heading=el('div',undefined,'flow-heading');heading.append(el('h2','用例流程图'),el('span','实线：前置依赖　虚线：结果路由　紫色虚线：当前可走分支','muted'));
  if(context.workflow){const label=el('label','图中状态所属环境'),choice=el('select');choice.id='flow-environment';choice.setAttribute('aria-label','流程图环境');
    const empty=el('option','请选择本轮环境');empty.value='';choice.append(empty);
    for(const env of context.environments){const option=el('option',env.label);option.value=env.id;choice.append(option);}
    choice.value=flow.environmentId??'';choice.onchange=()=>selectEnvironment(choice.value);label.append(choice);heading.append(label);}
  container.append(heading,el('p','展示全部用例；节点可点击打开。当前环境的执行阶段、未解决失败和过期证据分别显示。图中导航不会开始测试或保存结果。','muted'));
  if(flow.mode!=='managed')container.append(el('p',({definition:'方案定义：尚无本轮执行状态。',legacy:'旧流程：查看原始执行记录；不推断状态机或下一步。','environment-required':'请选择已加入本轮的环境，才能显示执行状态和下一步。'})[flow.mode],'context'));
  const scroll=el('div',undefined,'flow-scroll');scroll.tabIndex=0;scroll.setAttribute('aria-label','用例关系图，可滚动');
  const canvas=el('div',undefined,'flow-canvas');canvas.style.width=`${flow.width}px`;canvas.style.height=`${flow.height}px`;
  const drawing=svg('svg',{width:flow.width,height:flow.height,'aria-hidden':'true'}),defs=svg('defs',{}),markerId=`flow-arrow-${crypto.randomUUID()}`;
  const marker=svg('marker',{id:markerId,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'context-stroke'}));defs.append(marker);drawing.append(defs);
  const byId=new Map(flow.nodes.map(node=>[node.caseId,node]));
  flow.edges.forEach((edge,index)=>{
    const from=byId.get(edge.from),to=byId.get(edge.to),dependency=edge.kind==='dependency';
    const forward=dependency||to.x>from.x;
    const sx=from.x+from.width,sy=from.y+(dependency?48:94),tx=forward?to.x-5:to.x+to.width,ty=to.y+(dependency?48:edge.from===edge.to?36:94);
    const lane=Math.max(sx,tx)+32+(index%3)*16;
    const d=forward?`M ${sx} ${sy} C ${sx+40} ${sy}, ${tx-40} ${ty}, ${tx} ${ty}`:`M ${sx} ${sy} C ${lane} ${sy}, ${lane} ${ty}, ${tx} ${ty}`;
    const group=svg('g',{'data-kind':edge.kind,'data-from':edge.from,'data-to':edge.to,class:`flow-edge ${edge.kind}${edge.active?' active':''}`});
    const path=svg('path',{d,fill:'none','marker-end':`url(#${markerId})`});group.append(path);
    const title=svg('title',{});title.textContent=`${edge.from} → ${edge.to} · ${dependency?'前置依赖':edge.outcomes.map(value=>labels[value]).join('/')}`;group.append(title);
    drawing.append(group);
  });canvas.append(drawing);
  for(const node of flow.nodes){
    const current=node.caseId===caseId,next=node.caseId===flow.nextTest?.targetCaseId;
    const button=el('button',undefined,`flow-node${current?' current':''}${next?' next':''}`);button.type='button';button.dataset.caseId=node.caseId;button.dataset.state=node.state??flow.mode;
    button.title=`${node.caseId} · ${node.title}`;
    button.style.left=`${node.x}px`;button.style.top=`${node.y}px`;button.style.width=`${node.width}px`;button.style.height=`${node.height}px`;
    button.append(el('strong',node.caseId),el('span',node.title,'flow-title'),el('span',node.state?labels[node.state]:flow.mode==='legacy'?'旧流程':flow.mode==='definition'?'定义':'未选择环境',`pill ${node.state??''}`));
    if(current)button.append(el('span','当前','flow-badge'));if(next)button.append(el('span','下一步','flow-badge'));
    if(node.dependencyStale)button.append(el('span','证据已过期','flow-warning'));else if(node.unmetDependencies.length)button.append(el('span',`缺前置：${node.unmetDependencies.map(dep=>dep.caseId).join(', ')}`,'flow-warning'));
    if(node.unresolvedFailureId)button.append(el('span','有未解决失败','flow-warning'));
    button.onclick=()=>navigate(node.caseId);canvas.append(button);
  }
  scroll.append(canvas);container.append(scroll);
  const selected=byId.get(caseId);if(selected){scroll.scrollLeft=Math.max(0,selected.x-40);scroll.scrollTop=Math.max(0,selected.y-40);}
  const next=el('section',undefined,'flow-next');next.id='flow-next';next.setAttribute('aria-live','polite');
  const advice=flow.nextTest;
  next.append(el('strong',advice?`下一步测什么：${actions[advice.action]??advice.action}`:'下一步测什么：选择执行轮次与环境后显示'));
  if(advice){next.append(el('p',advice.reason));if(advice.resumeWhen)next.append(el('p',`恢复条件：${advice.resumeWhen}`));
    if(advice.target&&!advice.available)next.append(el('p','此建议当前不可执行，请先处理轮次状态或依赖变化。','flow-warning'));
    if(advice.unresolvedFailureId)next.append(el('p',`未解决失败：${advice.unresolvedFailureId}`,'flow-warning'));
    if(advice.target){next.append(el('p',`${advice.target.id} · ${advice.target.title}`),el('p',`步骤：${advice.target.steps}`,'prose'),el('p',`预期：${advice.target.expected}`,'prose'));
      if(byId.get(advice.target.id)?.dependencyStale)next.append(el('p','目标旧证据已过期，需要重新验证。','flow-warning'));
      if(advice.target.testLocation)next.append(el('p',`测试定位：${advice.target.testLocation.app??'应用未提供'} / ${advice.target.testLocation.screen}（操作前核对实际页面）`));
      const open=el('button',`打开 ${advice.target.id}`);open.disabled=!advice.available;open.type='button';open.onclick=()=>navigate(advice.target.id);next.append(open);}}
  container.append(next);
  const relationships=el('details');relationships.append(el('summary','查看关系明细（含结果分支）'));
  for(const edge of flow.edges)relationships.append(el('p',`${edge.from} → ${edge.to} · ${edge.kind==='dependency'?'前置依赖':`next：${edge.outcomes.map(value=>labels[value]).join(' / ')}`}${edge.active?' · 当前可走分支':''}`,'muted'));
  container.append(relationships);
}
export function renderTestLocation(container,item,context,message) {
  const hint=locationHint(item),section=el('section',undefined,'test-location');section.id='test-location';section.append(el('h3','手机 / 测试定位提示'));
  if(!hint.available)section.append(el('p','尚未配置页面和控件定位。可在当前用例定义中添加 testLocation；不要凭猜测操作。','muted'));
  else {
    section.append(el('p',`${hint.app??'应用未提供'} / ${hint.screen}`));
    const list=el('ol');for(const step of hint.entryPath??[])list.append(el('li',step));section.append(list);
    for(const target of hint.targets??[])section.append(el('p',`${target.name} · ${target.by}=${target.value}\n操作：${target.action}`,'prose'));
    if(hint.verify)section.append(el('p',`操作前核对：${hint.verify}`));
  }
  section.append(el('p','以上为计划提示，未核对当前设备界面。先用实际截图或界面树确认页面、控件和环境；不要凭旧坐标点击。','context'));
  const copy=el('button','复制手机测试提示');copy.type='button';copy.id='copy-test-location';
  copy.onclick=async()=>{try{await navigator.clipboard.writeText(formatTestLocation(item,context));message('测试提示已复制；操作前核对实际设备界面。');}catch{message('剪贴板不可用，请从本页或导出的 AI 快照读取测试定位信息。',true);}};
  section.append(copy);container.append(section);
}
