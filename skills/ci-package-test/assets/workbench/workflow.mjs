import {DEPENDENCIES, dependencyViews} from './dependencies.mjs';
import {TEST_LOCATION} from './test-location.mjs';
// JSON-compatible contract: shared by replay, UI action discovery and AI exports.
export const CONTRACT = {
  id: 'ci-package-test/workflow', version: 1,
  dependencies: DEPENDENCIES,
  testLocation: TEST_LOCATION,
  visualization:{projection:'projection.rounds[].flows',scope:'One frozen round and attached environment; null node states without a managed environment.',edges:{dependency:'Required upstream pass',next:'Outcome route; active only when the recommendation is available'},interaction:'Read-only navigation/copy. Use guarded start/result actions separately; graph never runs tests.'},
  conclusions:{format:'ci-package-test/conclusions',version:1,projection:'projection.conclusions',verdicts:['passed','failed','blocked','partial','incomplete','legacy'],persistence:'Saved with the archive revision in source documents or snapshots/<generation>/conclusions.json; file mode requires explicit Git commit.',approval:'A recorded-test conclusion is not release approval.'},
  identity: ['roundId', 'caseId', 'environmentId'],
  data: {
    archive: {schemaVersion:1, collections:['plans','environments','rounds','annotations'], revision:'optimistic concurrency counter'},
    case: {role:'definition', required:['id','title','priority','types','preconditions','steps','expected'], outcome:'none; result belongs to execution'},
    observation: {role:'immutable evidence', required:['id','caseId','environmentId','environment','status','executedAt','recordedAt','tester','notes','evidence'], context:'owning round pins plan/version/source/build and case definition',executedAt:'Timezone timestamp for execution; null only for pre-execution blocked/skipped defer' },
    workflow: {version:1, ordering:'events array; IDs immutable; divergent histories reject'},
    pending: 'untested is the machine key for pending; Chinese labels are presentation only'
  },
  round: {initial: 'draft', transitions: {
    prepare: {from: ['draft'], to: 'ready', guards: ['attached-environment']},
    begin: {from: ['ready'], to: 'running', guards: []},
    complete: {from: ['running'], to: 'completed', guards: ['all-executions-terminal']},
    reopen: {from: ['completed'], to: 'running', guards: ['reason']}
  }},
  execution: {initial: 'untested', transitions: {
    start: {from: ['untested', 'passed', 'failed', 'partial', 'blocked', 'skipped'], to: 'running', guards: ['round-running', 'attached-environment', 'dependencies-passed']},
    defer: {from: ['untested'], to: ['blocked', 'skipped'], guards: ['round-running', 'attached-environment', 'matching-observation', 'no-execution-time']},
    record: {from: ['running'], to: ['passed', 'failed', 'partial', 'blocked', 'skipped'], guards: ['round-running', 'matching-observation', 'prerequisite-evidence-current-unless-blocked-or-skipped']}
  }},
  unresolvedFailure: 'Keep the same case/environment failure ID through start, partial, blocked and skipped; only an observed pass clears it. Current execution phase and overall result are separate.',
  summaryPriority: ['failed', 'blocked', 'partial', 'running', 'untested', 'skipped', 'passed'],
  routing: {
    waitRequirement:'resumeWhen states the concrete condition that must be restored before retrying this case.',
    field:'case.next', outcomes:['passed','failed','partial','blocked','skipped'], actions:['test','retry','wait','done'],
    resultRequirements:{partial:['notes']}, requirementScope:'Cases with next branches; flat legacy cases keep their original contract.',
    semantics:{passed:'All required checks in this attempt met expectations.',failed:'An observed behavior violates an expected result; a diagnostic pass cannot clear it.',partial:'Only part was executed/verified; explain completed and unverified work. Any observed failure is failed.',blocked:'A missing prerequisite, account, environment or dependency prevents execution/continuation.',skipped:'An explicit scope/priority decision not to execute; requires reason and is not coverage.'},
    execution:'Guidance only: navigate to the explicit target; never auto-execute, auto-pass or infer skipped outcomes.',
    closure:'Freeze all reachable target cases in the round. Unvisited branches remain untested until explicitly recorded/skipped.'
  },
  resultRequirements: {passed: [], failed: ['notes', 'evidence'], partial: [], blocked: ['notes'], skipped: ['notes']},
  eventFields: ['id', 'scope', 'action', 'from', 'to', 'actor', 'at', 'reason'],
  executionEventFields: ['caseId', 'environmentId', 'observationId'],
  ordering: 'Append order is authoritative; timestamps describe events, not merge precedence. Import accepts prefix histories only.',
  legacy: 'Missing round.workflow means legacy observations; no inferred actor/start/lifecycle. New rounds use workflow.version=1.',
  annotations: {initial: 'open', comment: 'preserve-state', resolve: 'resolved', reopen: 'open', ordering: 'createdAt then event ID; original events retained'},
  definitions: 'Plans/cases are definitions, not execution outcomes. Round snapshots and observation evidence are immutable.',
  completion: 'completed means every case/environment has a terminal result; it does not mean all passed.'
};
export const RESULTS = Object.keys(CONTRACT.resultRequirements);
const require = (condition, message) => { if (!condition) throw new Error(message); };
const text = value => typeof value === 'string' && value.trim().length > 0;
const key = (caseId, environmentId) => JSON.stringify([caseId, environmentId]);
const time = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(`${value.slice(0,10)}T00:00:00Z`).toISOString().slice(0,10) === value.slice(0,10);
export function inspectWorkflow(round) {
  require(round.workflow && round.workflow.version === CONTRACT.version && Array.isArray(round.workflow.events), 'Invalid workflow contract');
  let state = CONTRACT.round.initial;
  const executions = new Map(), seen = new Set(), observed = new Set();
  const current = (caseId, environmentId) => executions.get(key(caseId,environmentId)) ?? {state: CONTRACT.execution.initial, attemptId: null, observationId: null, unresolvedFailureId: null, dependencyEvidence: []};
  const readiness=environmentId=>dependencyViews(round.cases,current,environmentId);
  const unfinished = () => round.environments.some(env=>[...readiness(env.id).values()].some(item=>!RESULTS.includes(item.state)||(item.state==='passed'&&item.dependencyStale)));
  for (const event of round.workflow.events) {
    require(event && text(event.id) && !seen.has(event.id), 'Invalid/duplicate workflow event ID');seen.add(event.id);
    require(text(event.actor) && time(event.at) && typeof event.reason === 'string', 'Workflow actor, timezone timestamp and reason text required');
    require(['round','execution'].includes(event.scope), 'Invalid workflow event scope');
    const transition = Object.hasOwn(CONTRACT[event.scope].transitions,event.action) ? CONTRACT[event.scope].transitions[event.action] : null;
    require(transition, 'Unknown workflow action');
    if (event.scope === 'round') {
      require(event.from === state && transition.from.includes(state) && event.to === transition.to, 'Invalid round transition/from-state');
      if (transition.guards.includes('attached-environment')) require(round.environments.length > 0, 'Round requires an attached environment');
      if (transition.guards.includes('all-executions-terminal')) require(!unfinished(), 'Round has unfinished executions');
      if (transition.guards.includes('reason')) require(text(event.reason), 'Reopen requires a reason');
      state = event.to;
    } else {
      require(state === 'running', 'Execution requires a running round');
      require(round.cases.some(item => item.id === event.caseId), 'Workflow case not found');
      require(round.environments.some(env => env.id === event.environmentId), 'Workflow environment not attached');
      const previous = current(event.caseId,event.environmentId);
      require(event.from === previous.state && transition.from.includes(previous.state), 'Invalid execution transition/from-state');
      if (event.action === 'start') {
        require(event.to === transition.to && event.observationId === '', 'Invalid start event');
        const dependencies=readiness(event.environmentId).get(event.caseId);
        require(dependencies.dependenciesSatisfied,`Prerequisites not passed: ${dependencies.unmetDependencies.map(item=>item.caseId).join(', ')}`);
        executions.set(key(event.caseId,event.environmentId),{...previous,state: event.to, attemptId: event.id,dependencyEvidence:dependencies.currentEvidence});
      } else {
        require(transition.to.includes(event.to), 'Invalid execution result');
        const observation = round.observations.find(item => item.id === event.observationId);
        require(observation && !observed.has(observation.id) && observation.caseId === event.caseId && observation.environmentId === event.environmentId && observation.status === event.to && observation.tester === event.actor && observation.recordedAt === event.at && observation.notes === event.reason, 'Workflow observation mismatch');
        const dependencies=readiness(event.environmentId).get(event.caseId);
        if(event.action==='record'&&!['blocked','skipped'].includes(event.to))require(!dependencies.dependencyStale,'Prerequisite evidence changed; record blocked and restart after prerequisites pass');
        if(event.action==='defer')require(observation.executedAt===null,'Deferred case requires executedAt=null; do not fabricate execution');
        const definition=round.cases.find(item=>item.id===event.caseId);
        const required=[...CONTRACT.resultRequirements[event.to],...(definition.next?CONTRACT.routing.resultRequirements[event.to]??[]:[])];
        for (const field of required) require(text(observation[field]), `${event.to} requires ${field}`);
        observed.add(observation.id);
        executions.set(key(event.caseId,event.environmentId),{state:event.to, attemptId:previous.attemptId,dependencyEvidence:previous.dependencyEvidence, observationId:observation.id,unresolvedFailureId:event.to==='passed'?null:event.to==='failed'?observation.id:previous.unresolvedFailureId});
      }
    }
  }
  require(observed.size === round.observations.length, 'Every managed observation requires a workflow event');
  const projected=new Map(round.environments.map(env=>[env.id,readiness(env.id)]));
  return {state, executions: round.cases.flatMap(item => round.environments.map(env => ({caseId:item.id,environmentId:env.id,...projected.get(env.id).get(item.id)})))};
}
export function roundActions(round) {
  const view = inspectWorkflow(round);
  return Object.entries(CONTRACT.round.transitions).filter(([,transition]) => transition.from.includes(view.state)).map(([action,transition]) => {
    const missing = transition.guards.filter(guard => guard === 'attached-environment' ? !round.environments.length : guard === 'all-executions-terminal' ? view.executions.some(item => !RESULTS.includes(item.state)||(item.state==='passed'&&item.dependencyStale)) : false);
    return {action,from:view.state,to:transition.to,allowed:!missing.length,missing,requiresReason:transition.guards.includes('reason')};
  });
}
