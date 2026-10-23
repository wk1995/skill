import {validateDependencies, orderCases} from './dependencies.mjs';
import {validateNext, validateTargets, nextTest} from './routing.mjs';
import {validateTestLocation, locationHint} from './test-location.mjs';
import {projectFlow} from './flow.mjs';
export {projectFlow};
export {nextTest};
import {CONTRACT, RESULTS, inspectWorkflow, roundActions} from './workflow.mjs';
export {CONTRACT, RESULTS, inspectWorkflow, roundActions};
export const TYPES = ['smoke', 'functional', 'performance', 'compatibility', 'stability', 'security', 'usability', 'install-upgrade', 'integration'];
export const STATUSES = [...RESULTS, 'running', 'untested'];
export const empty = () => ({schemaVersion: 1, revision: 0, plans: [], environments: [], rounds: [], annotations: []});
const copy = value => structuredClone(value);
const require = (ok, message) => { if (!ok) throw new Error(message); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, label, allowEmpty = false) => require(typeof value === 'string' && (allowEmpty || value.trim()), `${label}: text required`);
const list = (value, label) => require(Array.isArray(value), `${label}: array required`);
const find = (items, id, label) => { const item = items.find(entry => entry.id === id); require(item, `${label} not found: ${id}`); return item; };
function unique(items, label) {
  list(items, label);
  const ids = new Set();
  for (const item of items) {
    require(object(item), `${label}: object required`); text(item.id, `${label}.id`);
    require(!ids.has(item.id), `${label}: duplicate ID ${item.id}`); ids.add(item.id);
  }
}
const same = (a, b) => canonical(a) === canonical(b);
function canonical(value) {
  if (Array.isArray(value)) return JSON.stringify(value.map(item => JSON.parse(canonical(item))));
  if (object(value)) return JSON.stringify(Object.fromEntries(Object.keys(value).sort().map(key => [key, JSON.parse(canonical(value[key]))])));
  return JSON.stringify(value);
}
function timestamp(value, label) {
  text(value, label);
  require(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)), `${label}: timestamp with timezone required`);
  require(new Date(`${value.slice(0,10)}T00:00:00Z`).toISOString().slice(0,10) === value.slice(0,10), `${label}: invalid calendar date`);
}
function validateCase(item) {
  for (const key of ['id', 'title', 'priority', 'steps', 'expected']) text(item[key], `case.${key}`);
  text(item.preconditions, 'case.preconditions', true);
  list(item.types, 'case.types');
  require(item.types.length && new Set(item.types).size === item.types.length && item.types.every(type => TYPES.includes(type)), 'case: invalid types');
  validateNext(item);validateDependencies(item);validateTestLocation(item);
}
export function validatePlan(plan) {
  require(object(plan), 'plan: object required');
  for (const key of ['id', 'version', 'title', 'source', 'build', 'pr']) text(plan[key], `plan.${key}`, ['build', 'pr'].includes(key));
  require(Number.isSafeInteger(plan.revision) && plan.revision >= 0, 'plan: invalid revision');
  unique(plan.cases, 'plan.cases'); plan.cases.forEach(validateCase); validateTargets(plan.cases);orderCases(plan.cases);
  return plan;
}
function validateEnvironment(env) {
  require(object(env), 'environment: object required');
  for (const key of ['id', 'label', 'kind', 'configuration']) text(env[key], `environment.${key}`);
}
export function validate(state) {
  require(object(state) && state.schemaVersion === 1, 'Unsupported archive schema');
  require(Number.isSafeInteger(state.revision) && state.revision >= 0, 'Invalid state revision');
  unique(state.plans, 'plans'); state.plans.forEach(validatePlan);
  unique(state.environments, 'environments'); state.environments.forEach(validateEnvironment);
  unique(state.rounds, 'rounds');
  for (const round of state.rounds) {
    for (const key of ['id', 'name', 'planId', 'version', 'source', 'build', 'pr']) text(round[key], `round.${key}`, ['build', 'pr'].includes(key));
    const plan = find(state.plans, round.planId, 'Plan');
    require(round.version === plan.version, 'Round version must match its owning plan');
    timestamp(round.createdAt, 'round.createdAt');
    unique(round.cases, 'round.cases'); round.cases.forEach(validateCase); validateTargets(round.cases);orderCases(round.cases);
    require(round.cases.some(item => item.types.includes('smoke')), 'Round requires smoke coverage');
    unique(round.environments, 'round.environments');
    for (const env of round.environments) {
      validateEnvironment(env); require(same(env, find(state.environments, env.id, 'Environment')), 'Environment snapshot conflict');
    }
    unique(round.observations, 'observations');
    for (const observation of round.observations) {
      find(round.cases, observation.caseId, 'Case');
      const env = find(round.environments, observation.environmentId, 'Round environment');
      require(same(env, observation.environment), 'Observation environment conflict');
      require(STATUSES.includes(observation.status), 'Invalid result status');
      if(observation.executedAt===null)require(['blocked','skipped'].includes(observation.status)&&round.workflow?.events.some(event=>event.action==='defer'&&event.observationId===observation.id),'Missing execution time requires a deferred blocked/skipped event');
      else timestamp(observation.executedAt, 'executedAt');
      timestamp(observation.recordedAt, 'recordedAt');
      for (const key of ['tester', 'notes', 'evidence']) text(observation[key], `observation.${key}`, key !== 'tester');
    }
    if (round.workflow !== undefined) inspectWorkflow(round);
  }
  unique(state.annotations === undefined ? [] : state.annotations, 'annotations');
  for (const note of state.annotations ?? []) validateAnnotation(state, note);
  return state;
}
export function annotationContext(state, input) {
  const plan = find(state.plans, input.planId, 'Plan');
  const round = input.roundId ? find(state.rounds, input.roundId, 'Round') : null;
  require(!round || round.planId === plan.id, 'Annotation round belongs to another plan');
  const item = find(round?.cases ?? plan.cases, input.caseId, 'Annotation case');
  const observation = input.observationId ? find(round?.observations ?? [], input.observationId, 'Annotation observation') : null;
  require(!observation || observation.caseId === item.id, 'Annotation observation belongs to another case');
  return {version: round?.version ?? plan.version, source: round?.source ?? plan.source, planTitle: plan.title,
    roundName: round?.name ?? '', case: copy(item), observation: observation ? copy(observation) : null};
}
function targetText(context, field) {
  if (field === 'case') return [context.case.title, context.case.preconditions, context.case.steps, context.case.expected].join('\n');
  if (field === 'observation') {
    require(context.observation, 'Annotation has no observation target');
    return [context.observation.status, context.observation.tester, context.observation.notes, context.observation.evidence].join('\n');
  }
  require(['preconditions', 'steps', 'expected'].includes(field), 'Invalid annotation field');
  return context.case[field];
}
function validateAnnotation(state, note) {
  for (const key of ['id', 'planId', 'caseId', 'roundId', 'observationId']) text(note[key], `annotation.${key}`, ['roundId','observationId'].includes(key));
  const plan = find(state.plans, note.planId, 'Annotation plan');
  require(['web', 'browser'].includes(note.origin), 'Invalid annotation origin');
  require(object(note.context) && object(note.target), 'Annotation context and target required');
  for (const key of ['version','source','planTitle','roundName']) text(note.context[key], `annotation.context.${key}`, key === 'roundName');
  validateCase(note.context.case); require(note.context.case.id === note.caseId, 'Annotation case snapshot conflict');
  require(note.context.version === plan.version, 'Annotation version conflict');
  if (note.roundId) {
    const round = find(state.rounds, note.roundId, 'Annotation round');
    require(round.planId === note.planId && round.source === note.context.source && same(find(round.cases,note.caseId,'Annotation case'),note.context.case), 'Annotation round snapshot conflict');
  }
  if (note.observationId) {
    const round = find(state.rounds, note.roundId, 'Annotation observation round');
    const observation = find(round.observations, note.observationId, 'Annotation observation');
    require(observation.caseId === note.caseId && same(observation, note.context.observation), 'Annotation observation snapshot conflict');
  } else require(note.context.observation === null, 'Unexpected annotation observation snapshot');
  text(note.target.quote, 'annotation quote', true);
  const content = targetText(note.context, note.target.field);
  require(!note.target.quote || content.includes(note.target.quote), 'Annotation quote does not match its snapshot');
  unique(note.events, 'annotation events');require(note.events.length > 0 && note.events[0].kind === 'comment', 'Annotation must start with a comment');
  for (const event of note.events) {
    require(['comment','resolve','reopen'].includes(event.kind), 'Invalid annotation event kind');
    text(event.author, 'annotation author');text(event.body, 'annotation body', event.kind !== 'comment');timestamp(event.createdAt, 'annotation event time');
  }
}
export const annotationsFor = (state, context) => (state.annotations ?? []).filter(note => note.planId === context.planId && note.roundId === (context.roundId ?? '') && (!context.caseId || note.caseId === context.caseId) && (!context.observationId || note.observationId === context.observationId));
export const orderedAnnotationEvents = note => [...note.events].sort((a,b) => Date.parse(a.createdAt)-Date.parse(b.createdAt) || (a.id===b.id?0:a.id<b.id?-1:1));
export function annotationStatus(note) {
  const latest = orderedAnnotationEvents(note).filter(event => event.kind !== 'comment').at(-1);
  return latest?.kind === 'resolve' ? 'resolved' : 'open';
}
export function addAnnotation(state, input) {
  validate(state);
  require(!(state.annotations ?? []).some(note => note.id === input.id), 'Annotation ID already exists');
  const context = annotationContext(state, input);
  require(!input.expectedContext || same(context, input.expectedContext), 'Annotation definition changed; reload and review');
  const note = {id:input.id,planId:input.planId,roundId:input.roundId??'',caseId:input.caseId,observationId:input.observationId??'',
    origin:input.origin??'web',context,target:copy(input.target),events:[copy(input.event)]};
  return change(state, next => { next.annotations ??= [];next.annotations.push(note); });
}
export function addAnnotationEvent(state, noteId, event) {
  validate(state);const note = find(state.annotations ?? [], noteId, 'Annotation');
  const old = note.events.find(item => item.id === event.id);
  if (old) { require(same(old,event), 'Conflicting annotation event');return state; }
  require(['comment','resolve','reopen'].includes(event.kind), 'Invalid annotation event kind');
  if ((event.kind === 'resolve' && annotationStatus(note) === 'resolved') || (event.kind === 'reopen' && annotationStatus(note) === 'open')) {
    // A no-op still validates the supplied event before returning success.
    text(event.id,'annotation event ID');text(event.author,'annotation author');text(event.body,'annotation body',true);timestamp(event.createdAt,'annotation event time');return state;
  }
  return change(state, next => find(next.annotations,noteId,'Annotation').events.push(copy(event)));
}
function change(state, action) {
  validate(state);
  const next = copy(state); action(next); next.revision++;
  return validate(next);
}
export function importPlan(state, plan) {
  validate(state); validatePlan(plan);
  const old = state.plans.find(item => item.id === plan.id);
  if (old && same(old, plan)) return state;
  require(!old || old.version === plan.version, 'Plan identity cannot change version; create another plan');
  require(!old || plan.revision > old.revision, 'Stale/conflicting plan revision');
  return change(state, next => {
    next.plans = next.plans.filter(item => item.id !== plan.id); next.plans.push(copy(plan));
  });
}
export function editCase(state, planId, item) {
  validateCase(item);
  const plan = copy(find(state.plans, planId, 'Plan'));
  find(plan.cases, item.id, 'Case'); plan.cases = plan.cases.map(entry => entry.id === item.id ? copy(item) : entry);
  plan.revision++; return importPlan(state, plan);
}
export function registerEnvironment(state, env) {
  validateEnvironment(env);
  require(!state.environments.some(item => item.id === env.id), 'Environment ID already registered');
  return change(state, next => next.environments.push(copy(env)));
}
export function attachEnvironment(state, roundId, environmentId) {
  validate(state);
  const round = find(state.rounds, roundId, 'Round'); const env = find(state.environments, environmentId, 'Environment');
  if (round.environments.some(item => item.id === environmentId)) return state;
  if (round.workflow) require(['draft','ready'].includes(inspectWorkflow(round).state), 'Attach environments before beginning the round');
  return change(state, next => find(next.rounds, roundId, 'Round').environments.push(copy(env)));
}
export function statusOf(round, caseId) {
  const latest = new Map();
  const priority = CONTRACT.summaryPriority;
  if (round.workflow) {
    const statuses = inspectWorkflow(round).executions.filter(item => item.caseId === caseId).map(item => item.unresolvedFailureId?'failed':item.dependencyStale&&['passed','running'].includes(item.state)?'blocked':item.state);
    return priority.find(status => statuses.includes(status)) ?? 'untested';
  }
  for (const item of round.observations.filter(item => item.caseId === caseId)) {
    const old = latest.get(item.environmentId);
    const order = old ? Date.parse(item.executedAt) - Date.parse(old.executedAt) || Date.parse(item.recordedAt) - Date.parse(old.recordedAt) : 1;
    if (!old || order > 0 || (order === 0 && priority.indexOf(item.status) < priority.indexOf(old.status))) latest.set(item.environmentId, item);
  }
  const statuses = round.environments.map(env => latest.get(env.id)?.status ?? 'untested');
  return priority.find(status => statuses.includes(status)) ?? 'untested';
}
export const roundsFor = (state, planId) => state.rounds.filter(round => round.planId === planId).sort((a,b) => Date.parse(a.createdAt) - Date.parse(b.createdAt));
export function createRound(state, input) {
  validate(state);
  text(input.id, 'round ID'); text(input.name, 'round name'); timestamp(input.createdAt, 'createdAt');
  require(!state.rounds.some(item => item.id === input.id), 'Round ID already exists');
  const plan = find(state.plans, input.planId, 'Plan');
  const previous = roundsFor(state, input.planId).at(-1);
  const current = new Map(plan.cases.map(item => [item.id, item]));
  const selected = new Map();
  const add = (item, reason) => {
    if (!selected.has(item.id)) selected.set(item.id, {...copy(current.get(item.id) ?? item), selectionReasons: []});
    const reasons = selected.get(item.id).selectionReasons; if (!reasons.includes(reason)) reasons.push(reason);
  };
  if (previous) previous.cases.filter(item => statusOf(previous, item.id) === 'failed').forEach(item => add(item, 'previous-failure'));
  plan.cases.filter(item => item.types.includes('smoke')).forEach(item => add(item, 'smoke'));
  require(plan.cases.some(item => item.types.includes('smoke')), 'Define smoke cases before starting a round');
  const changedIds = input.changedIds ?? (previous ? [] : plan.cases.map(item => item.id));
  list(changedIds, 'changedIds'); changedIds.forEach(id => add(find(plan.cases, id, 'Changed case'), 'change'));
  if (input.includeUnfinished && previous) previous.cases.filter(item => statusOf(previous, item.id) !== 'passed').forEach(item => add(item, 'unfinished'));
  // Freeze the complete reachable branch graph; map iteration visits newly added targets once.
  for(const item of selected.values()) {
    for(const id of item.dependsOn??[]){const target=current.get(id)??previous?.cases.find(entry=>entry.id===id);require(target,`Dependency case not found: ${id}`);add(target,'dependency');}
    for(const status of RESULTS) {
      const route=item.next?.[status];
      if(route&&['test','retry'].includes(route.action)) {
        const target=current.get(route.caseId)??previous?.cases.find(entry=>entry.id===route.caseId);
        require(target,`Next case not found: ${route.caseId}`);add(target,'conditional-next');
      }
    }
  }
  const round = {id: input.id, name: input.name, planId: plan.id, version: plan.version, source: plan.source,
    build: plan.build, pr: plan.pr, createdAt: input.createdAt, cases: orderCases([...selected.values()]), environments: [], observations: [], workflow: {version: CONTRACT.version, events: []}};
  return change(state, next => next.rounds.push(round));
}
export function record(state, roundId, observation) {
  return recordBatch(state, roundId, [observation]);
}
export function recordBatch(state, roundId, observations) {
  validate(state);
  unique(observations, 'new observations'); require(observations.length, 'Select at least one case');
  const round = find(state.rounds, roundId, 'Round');
  for (const observation of observations) require(!round.observations.some(item => item.id === observation.id), 'Observation ID already exists');
  // Full validation includes every new observation before the caller can persist.
  return change(state, next => {
    const target = find(next.rounds, roundId, 'Round');
    const executions=target.workflow?inspectWorkflow(target).executions:[];
    target.observations.push(...copy(observations));
    if (target.workflow) for (const observation of observations) {
      const from=executions.find(entry=>entry.caseId===observation.caseId&&entry.environmentId===observation.environmentId)?.state;
      const action=from==='untested'&&CONTRACT.execution.transitions.defer.to.includes(observation.status)?'defer':'record';
      target.workflow.events.push({
      id:`result:${observation.id}`,scope:'execution',action,from,to:observation.status,
      actor:observation.tester,at:observation.recordedAt,reason:observation.notes,
      caseId:observation.caseId,environmentId:observation.environmentId,observationId:observation.id
    });
    }
  });
}
export function importArchive(state, incoming) {
  validate(state); validate(incoming);
  const next = copy(state);
  for (const plan of incoming.plans) {
    const old = next.plans.find(item => item.id === plan.id);
    if (!old) next.plans.push(copy(plan));
    else if (!same(old, plan)) {
      require(old.version === plan.version && plan.revision > old.revision, 'Stale/conflicting plan revision');
      next.plans[next.plans.indexOf(old)] = copy(plan);
    }
  }
  for (const env of incoming.environments) {
    const old = next.environments.find(item => item.id === env.id);
    require(!old || same(old, env), 'Conflicting registered environment');
    if (!old) next.environments.push(copy(env));
  }
  for (const round of incoming.rounds) {
    const old = next.rounds.find(item => item.id === round.id);
    if (!old) { next.rounds.push(copy(round)); continue; }
    const fixed = item => Object.fromEntries(Object.entries(item).filter(([key]) => !['environments', 'observations', 'workflow'].includes(key)));
    require(same(fixed(old), fixed(round)), 'Conflicting historical round definition');
    require((old.workflow === undefined) === (round.workflow === undefined), 'Cannot upgrade/downgrade historical workflow');
    if (old.workflow) {
      require(old.workflow.version === round.workflow.version, 'Conflicting workflow version');
      const left = old.workflow.events, right = round.workflow.events;
      require(left.slice(0,Math.min(left.length,right.length)).every((event,index) => same(event,right[index])), 'Divergent workflow history');
      if (right.length > left.length) old.workflow.events = copy(right);
    }
    for (const env of round.environments) if (!old.environments.some(item => item.id === env.id)) old.environments.push(copy(env));
    for (const observation of round.observations) {
      const existing = old.observations.find(item => item.id === observation.id);
      require(!existing || same(existing, observation), 'Conflicting historical observation');
      if (!existing) old.observations.push(copy(observation));
    }
  }
  for (const note of incoming.annotations ?? []) {
    next.annotations ??= [];
    const old = next.annotations.find(item => item.id === note.id);
    if (!old) { next.annotations.push(copy(note));continue; }
    const fixed = item => Object.fromEntries(Object.entries(item).filter(([key]) => key !== 'events'));
    require(same(fixed(old),fixed(note)), 'Conflicting annotation context');
    for (const event of note.events) {
      const existing = old.events.find(item => item.id === event.id);
      require(!existing || same(existing,event), 'Conflicting annotation event');
      if (!existing) old.events.push(copy(event));
    }
  }
  validate(next);
  if (same(next, state)) return state;
  next.revision++; return next;
}

export function transitionRound(state, roundId, input) {
  validate(state);
  const round = find(state.rounds,roundId,'Round');
  require(round.workflow, 'Legacy round: create a new managed round');
  const transition = Object.hasOwn(CONTRACT.round.transitions,input.action) ? CONTRACT.round.transitions[input.action] : null;
  require(transition, 'Unknown round action');
  const event = {id:input.id,scope:'round',action:input.action,from:input.from,to:transition.to,actor:input.actor,at:input.at,reason:input.reason??''};
  return appendWorkflowEvent(state,roundId,event);
}
export function startExecution(state, roundId, input) {
  validate(state);
  return appendWorkflowEvent(state,roundId,{id:input.id,scope:'execution',action:'start',from:input.from,to:'running',
    actor:input.actor,at:input.at,reason:input.reason??'',caseId:input.caseId,environmentId:input.environmentId,observationId:''});
}
function appendWorkflowEvent(state,roundId,event) {
  const round = find(state.rounds,roundId,'Round');
  require(round.workflow, 'Legacy round: create a new managed round');
  const old = round.workflow.events.find(item => item.id === event.id);
  if (old) { require(same(old,event), 'Conflicting workflow event');return state; }
  return change(state,next => find(next.rounds,roundId,'Round').workflow.events.push(event));
}
export function executionState(round,caseId,environmentId) {
  return inspectWorkflow(round).executions.find(item => item.caseId === caseId && item.environmentId === environmentId)?.state ?? 'untested';
}
export function exportAI(state) {
  validate(state);
  return {format:'ci-package-test/ai-snapshot',contract:copy(CONTRACT),archive:copy(state),projection:{
    rounds:state.rounds.map(round => {
      if (!round.workflow) return {roundId:round.id,state:'legacy',nextActions:[],cases:round.cases.map(item=>({caseId:item.id,status:statusOf(round,item.id)}))};
      const view = inspectWorkflow(round);
      return {roundId:round.id,state:view.state,nextActions:roundActions(round),flows:round.environments.map(env=>projectFlow(round,{environmentId:env.id})),executions:view.executions.map(item => ({...item,
        testLocation:locationHint(round.cases.find(entry=>entry.id===item.caseId)),
        nextTest:nextTest(round,item.caseId,item.environmentId),
        nextActions:view.state !== 'running' ? [] : item.state === 'running' ? RESULTS.filter(result=>!item.dependencyStale||['blocked','skipped'].includes(result)).map(result=>({action:'record',to:result,required:[...CONTRACT.resultRequirements[result],...(round.cases.find(entry=>entry.id===item.caseId).next?CONTRACT.routing.resultRequirements[result]??[]:[])]})) : [...(item.dependenciesSatisfied?[{action:'start',from:item.state,to:'running'}]:[]),...(item.state==='untested'?CONTRACT.execution.transitions.defer.to.map(to=>({action:'defer',from:item.state,to,required:[...CONTRACT.resultRequirements[to],'executedAt'],values:{executedAt:null}})):[])]
      }))};
    }),annotations:(state.annotations??[]).map(note=>({annotationId:note.id,state:annotationStatus(note)}))
  }};
}

export function startExecutionBatch(state,roundId,inputs) {
  validate(state);unique(inputs,'execution starts');require(inputs.length,'Select at least one case');
  let next=state;
  for(const input of inputs) next=startExecution(next,roundId,input);
  if(next===state)return state;
  next.revision=state.revision+1;return validate(next);
}
