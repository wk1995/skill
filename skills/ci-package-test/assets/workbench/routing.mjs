import {CONTRACT, RESULTS, inspectWorkflow} from './workflow.mjs';
const require=(value,message)=>{if(!value)throw new Error(message);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&value.trim().length>0;
export function validateNext(item) {
  if(item.next===undefined)return;
  require(object(item.next),'case.next: outcome map required');
  require(Object.keys(item.next).length===RESULTS.length&&RESULTS.every(status=>Object.hasOwn(item.next,status)),'case.next: define exactly all five result branches');
  for(const status of RESULTS) {
    const route=item.next[status];
    require(object(route)&&CONTRACT.routing.actions.includes(route.action)&&text(route.reason),`case.next.${status}: valid action and reason required`);
    const fields=['action','reason',...(['test','retry'].includes(route.action)?['caseId']:route.action==='wait'?['resumeWhen']:[])];
    require(Object.keys(route).every(field=>fields.includes(field)),'Unsupported next-test branch field');
    if(['test','retry'].includes(route.action)) {
      require(text(route.caseId),`case.next.${status}: target case ID required`);
      require(route.action!=='retry'||route.caseId===item.id,'retry must target the same case');
    } else require(!Object.hasOwn(route,'caseId'),'wait/done must not contain a hidden case target');
    if(route.action==='wait')require(text(route.resumeWhen),'wait branch requires a concrete resumeWhen condition');
  }
}
export function validateTargets(cases) {
  const ids=new Set(cases.map(item=>item.id));
  for(const item of cases) {
    validateNext(item);
    for(const route of Object.values(item.next??{}))if(['test','retry'].includes(route.action))require(ids.has(route.caseId),`Next case not found: ${route.caseId}`);
  }
}
export function nextTest(round,caseId,environmentId) {
  const item=round.cases.find(entry=>entry.id===caseId);
  require(item,'Next-test case not found');require(round.environments.some(env=>env.id===environmentId),'Next-test environment not attached');
  validateTargets(round.cases);
  if(!round.workflow)return {action:'unavailable',reason:'Legacy round: prepare a managed round for environment-bound routing.'};
  const view=inspectWorkflow(round),execution=view.executions.find(entry=>entry.caseId===caseId&&entry.environmentId===environmentId);
  const observation=round.observations.find(entry=>entry.id===execution.observationId);
  const context={roundId:round.id,caseId,environmentId,state:execution.state,unresolvedFailureId:execution.unresolvedFailureId,basedOnObservationId:observation?.id??null,notes:observation?.notes??'',evidence:observation?.evidence??''};
  if(!RESULTS.includes(execution.state))return {...context,action:'current',reason:'Execute or continue the current case before selecting an outcome branch.',target:structuredClone(item),available:view.state==='running'};
  if(!item.next)return {...context,action:'unconfigured',reason:'No next-test branch is defined for this case; do not infer the next test.'};
  const route=item.next[execution.state];
  const target=['test','retry'].includes(route.action)?structuredClone(round.cases.find(entry=>entry.id===route.caseId)):null;
  return {...context,action:route.action,reason:route.reason,...(route.action==='wait'?{resumeWhen:route.resumeWhen}:{}),target,available:view.state==='running'&&Boolean(target),targetCaseId:target?.id??null,
    targetState:target?view.executions.find(entry=>entry.caseId===target.id&&entry.environmentId===environmentId).state:null};
}
