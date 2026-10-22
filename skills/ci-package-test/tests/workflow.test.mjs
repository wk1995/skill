import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
const at='2026-10-22T10:00:00Z';
const env=id=>({id,label:id,kind:'browser',configuration:'isolated fixture'});
const event=(id,action,from,extra={})=>({id,action,from,actor:'Tester',at,reason:'',...extra});
function fixture() {
  let state=m.importPlan(m.empty(),{id:'p',revision:0,version:'v1',title:'Fixture',source:'sha',build:'',pr:'',cases:['A','B'].map(id=>({id,title:id,priority:'P0',types:['smoke'],preconditions:'Ready',steps:'Exercise',expected:'Observe'}))});
  state=m.createRound(state,{id:'r',name:'Round',planId:'p',createdAt:at});return state;
}
const round=state=>state.rounds[0];
function running() {
  let state=fixture();state=m.registerEnvironment(state,env('e'));state=m.attachEnvironment(state,'r','e');
  state=m.transitionRound(state,'r',event('prepare','prepare','draft'));return m.transitionRound(state,'r',event('begin','begin','ready'));
}
const start=(state,id='A',suffix='')=>m.startExecution(state,'r',{...event(`start-${id}${suffix}`,'start',m.executionState(round(state),id,'e')),caseId:id,environmentId:'e'});
const observation=(id,caseId='A',status='passed',extra={})=>({id,caseId,status,environmentId:'e',environment:env('e'),executedAt:at,recordedAt:at,tester:'Tester',notes:'Observed reason',evidence:'fixture screenshot',...extra});
function rejects(state,action,pattern) {const before=structuredClone(state);assert.throws(()=>action(state),pattern);assert.deepEqual(state,before);}

test('round lifecycle guards, actor/time/from checks and exact retry are enforced on direct invocation',()=>{
  let state=fixture();assert.equal(m.inspectWorkflow(round(state)).state,'draft');
  rejects(state,s=>m.transitionRound(s,'r',event('x','prepare','draft')),/attached/);
  state=m.registerEnvironment(state,env('e'));state=m.attachEnvironment(state,'r','e');
  for(const input of [event('x','begin','draft'),event('x','prepare','ready'),event('x','prepare','draft',{actor:''}),event('x','prepare','draft',{at:'yesterday'}),event('x','constructor','draft')]) rejects(state,s=>m.transitionRound(s,'r',input));
  const input=event('prepare','prepare','draft');state=m.transitionRound(state,'r',input);assert.equal(m.transitionRound(state,'r',input),state);
  rejects(state,s=>m.transitionRound(s,'r',{...input,actor:'Other'}),/Conflicting/);
  state=m.transitionRound(state,'r',event('begin','begin','ready'));assert.equal(m.inspectWorkflow(round(state)).state,'running');
  state=m.registerEnvironment(state,env('other'));rejects(state,s=>m.attachEnvironment(s,'r','other'),/before beginning/);
  assert.equal(m.attachEnvironment(state,'r','e'),state);
});

test('results require explicit execution start; every terminal result follows the shared contract',()=>{
  for(const result of m.RESULTS) {
    let state=running();rejects(state,s=>m.record(s,'r',observation('early','A',result)),/transition/);
    state=start(state);assert.equal(m.statusOf(round(state),'A'),'running');
    rejects(state,s=>start(s),/Conflicting|transition/);
    state=m.record(state,'r',observation('result','A',result));assert.equal(m.executionState(round(state),'A','e'),result);
    const view=m.exportAI(state).projection.rounds[0].executions.find(item=>item.caseId==='A');
    assert.deepEqual(view.nextActions,[{action:'start',from:result,to:'running'}]);
    rejects(state,s=>m.record(s,'r',observation('without-restart','A',result)),/transition/);
  }
});

test('blocked and skipped need reasons; failure needs reason and evidence; bad batch preserves all state',()=>{
  let state=start(start(running()),'B');
  for(const [status,field] of [['failed','notes'],['failed','evidence'],['blocked','notes'],['skipped','notes']]) {
    const bad=observation('bad','B',status,{[field]:' '});
    rejects(state,s=>m.record(s,'r',bad),new RegExp(`requires ${field}`));
    rejects(state,s=>m.recordBatch(s,'r',[observation('good'),bad]),new RegExp(`requires ${field}`));
  }
  for(const status of ['untested','running','invented']) rejects(state,s=>m.record(s,'r',observation('bad','A',status)));
  state=m.recordBatch(state,'r',[observation('one'),observation('two','B','skipped')]);assert.equal(round(state).observations.length,2);
});

test('complete rejects pending or running pairs, reopen needs reason, retest preserves snapshots and outcomes',()=>{
  let state=running();rejects(state,s=>m.transitionRound(s,'r',event('done','complete','running')),/unfinished/);
  state=start(state);rejects(state,s=>m.transitionRound(s,'r',event('done','complete','running')),/unfinished/);
  state=m.record(state,'r',observation('failure','A','failed'));state=start(state,'B');state=m.record(state,'r',observation('skip','B','skipped'));
  state=m.transitionRound(state,'r',event('done','complete','running'));assert.equal(m.inspectWorkflow(round(state)).state,'completed');assert.equal(m.statusOf(round(state),'A'),'failed');
  rejects(state,s=>start(s,'A','again'),/running round/);rejects(state,s=>m.record(s,'r',observation('closed')),/running round/);
  rejects(state,s=>m.transitionRound(s,'r',event('open','reopen','completed')),/reason/);
  const old=structuredClone(round(state));state=m.transitionRound(state,'r',event('open','reopen','completed',{reason:'Verify fix'}));
  state=start(state,'A','again');state=m.record(state,'r',observation('retest','A','passed'));
  assert.equal(m.statusOf(round(state),'A'),'passed');assert.deepEqual(round(state).observations.slice(0,2),old.observations);assert.deepEqual(round(state).cases,old.cases);
  assert.deepEqual(round(state).workflow.events.slice(0,old.workflow.events.length),old.workflow.events);
});

test('execution identity is round/case/environment; another environment cannot clear failure',()=>{
  let state=fixture();for(const id of ['e','f']){state=m.registerEnvironment(state,env(id));state=m.attachEnvironment(state,'r',id);}
  state=m.transitionRound(state,'r',event('prepare','prepare','draft'));state=m.transitionRound(state,'r',event('begin','begin','ready'));
  state=start(state);state=m.record(state,'r',observation('failed','A','failed'));
  state=m.startExecution(state,'r',{...event('f-start','start','untested'),caseId:'A',environmentId:'f'});
  state=m.record(state,'r',observation('other-pass','A','passed',{environmentId:'f',environment:env('f')}));
  assert.equal(m.statusOf(round(state),'A'),'failed');assert.equal(m.executionState(round(state),'B','e'),'untested');
  state=m.createRound(state,{id:'next',name:'Next',planId:'p',createdAt:at,changedIds:[]});assert.equal(m.statusOf(state.rounds[1],'A'),'untested');
});

test('start batch validates atomically and repeats idempotently; wrong identity/from cannot bypass replay',()=>{
  const state=running(),inputs=['A','B'].map(caseId=>({...event(caseId,'start','untested'),caseId,environmentId:'e'}));
  rejects(state,s=>m.startExecutionBatch(s,'r',[]),/at least one/);
  for(const extra of [{caseId:'missing'},{environmentId:'missing'},{actor:''},{from:'passed'},{id:'A'}]) rejects(state,s=>m.startExecutionBatch(s,'r',[inputs[0],{...inputs[1],...extra}]));
  const next=m.startExecutionBatch(state,'r',inputs);assert.equal(next.revision,state.revision+1);assert.equal(m.startExecutionBatch(next,'r',inputs),next);
  for(const id of ['A','B'])assert.equal(m.executionState(round(next),id,'e'),'running');
});

test('prefix imports retain event order and history, reject branches/downgrades/invalid late events',()=>{
  const base=running();let newer=start(base);newer=m.record(newer,'r',observation('o'));
  assert.deepEqual(m.importArchive(base,newer).rounds,newer.rounds);assert.equal(m.importArchive(newer,base),newer);assert.equal(m.importArchive(newer,structuredClone(newer)),newer);
  const branch=start(base,'B');rejects(newer,s=>m.importArchive(s,branch),/Divergent/);
  for(const edit of [r=>delete r.workflow,r=>r.workflow.version=99,r=>r.workflow.events.at(-1).from='passed',r=>r.workflow.events.at(-1).actor='Someone else',r=>r.workflow.events.at(-1).reason='Rewritten',r=>r.workflow.events.push({...r.workflow.events[0],id:'late',from:'draft'})]) {
    const incoming=structuredClone(newer);edit(round(incoming));rejects(newer,s=>m.importArchive(s,incoming));
  }
  const missing=structuredClone(newer);round(missing).workflow.events.pop();rejects(base,s=>m.importArchive(s,missing),/Every managed observation/);
  const reordered=structuredClone(newer);round(reordered).workflow.events.reverse();rejects(base,s=>m.importArchive(s,reordered));
});

test('legacy archives are explicit, keep observations untouched and use new managed rounds for future work',()=>{
  let state=fixture();delete round(state).workflow;state=m.registerEnvironment(state,env('e'));state=m.attachEnvironment(state,'r','e');
  state=m.record(state,'r',observation('old','A','failed',{notes:'',evidence:''}));const original=structuredClone(round(state));
  const restored=m.importArchive(m.empty(),JSON.parse(JSON.stringify(state)));assert.deepEqual(round(restored),original);
  const projection=m.exportAI(restored).projection.rounds[0];assert.equal(projection.state,'legacy');assert.deepEqual(projection.nextActions,[]);
  rejects(state,s=>m.transitionRound(s,'r',event('x','prepare','draft')),/Legacy/);
  state=m.createRound(state,{id:'next',name:'Next',planId:'p',createdAt:at,changedIds:[]});assert.equal(m.inspectWorkflow(state.rounds[1]).state,'draft');assert.deepEqual(round(state),original);
});

test('AI snapshot uses the same contract, exports original evidence and guarded next actions without mutation',()=>{
  const state=fixture(),before=structuredClone(state),packet=m.exportAI(state);
  assert.deepEqual(JSON.parse(JSON.stringify(packet)).contract,m.CONTRACT);assert.deepEqual(packet.archive,state);assert.deepEqual(state,before);
  assert.deepEqual(packet.projection.rounds[0].nextActions,[{action:'prepare',from:'draft',to:'ready',allowed:false,missing:['attached-environment'],requiresReason:false}]);
  const active=start(running());const actions=m.exportAI(active).projection.rounds[0].executions[0].nextActions;
  assert.deepEqual(actions.find(item=>item.to==='failed').required,['notes','evidence']);
  packet.archive.rounds[0].name='Mutated copy';assert.deepEqual(state,before);
});

test('managed all-pass no-diff rounds rerun smoke, preserve definitions and keep annotation state separate',()=>{
  let state=start(start(running()),'B');state=m.recordBatch(state,'r',[observation('a-pass'),observation('b-pass','B')]);
  state=m.addAnnotation(state,{id:'note',planId:'p',roundId:'r',caseId:'A',observationId:'a-pass',target:{field:'observation',quote:'Observed reason'},event:{id:'comment',kind:'comment',author:'Reviewer',body:'Check this evidence',createdAt:at}});
  state=m.addAnnotationEvent(state,'note',{id:'resolved',kind:'resolve',author:'Reviewer',body:'Reviewed',createdAt:at});
  assert.equal(m.exportAI(state).projection.annotations[0].state,'resolved');assert.equal(m.statusOf(round(state),'A'),'passed');
  state=m.transitionRound(state,'r',event('done','complete','running'));const old=structuredClone(round(state));
  state=m.editCase(state,'p',{...state.plans[0].cases[0],steps:'Updated procedure'});
  state=m.createRound(state,{id:'next',name:'Next',planId:'p',createdAt:at,changedIds:[]});
  assert.deepEqual(state.rounds[1].cases.map(item=>item.id),['A','B']);assert.equal(state.rounds[1].cases[0].steps,'Updated procedure');
  assert.equal(m.statusOf(state.rounds[1],'A'),'untested');assert.deepEqual(round(state),old);
});

test('invalid existing workflow is rejected even on idempotent sibling operations',()=>{
  const state=running();round(state).workflow.events[1].from='draft';
  for(const action of [s=>m.attachEnvironment(s,'r','e'),s=>m.importPlan(s,s.plans[0]),s=>m.importArchive(s,s),s=>m.transitionRound(s,'r',event('prepare','prepare','draft')),s=>m.startExecutionBatch(s,'r',[]),s=>m.exportAI(s)]) rejects(state,action,/transition/);
});
