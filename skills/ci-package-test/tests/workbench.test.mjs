import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';

const time='2026-10-22T04:00:00Z';
const caseOf=(id,types=['functional'])=>({id,title:`Case ${id}`,priority:'P1',types,preconditions:'Ready',steps:'Exercise behavior',expected:'Expected behavior'});
const plan=()=>({id:'plan',revision:0,version:'1.2.3',title:'Regression',source:'exact-source-sha',build:'https://example.invalid/run/1',pr:'https://example.invalid/pr/1',cases:[caseOf('constructor',['smoke','functional']),caseOf('FAIL'),caseOf('CHANGE')]});
const environment=id=>({id,label:'Same model',kind:'browser',configuration:'Same OS/browser; distinct physical instance'});
const round=(state,id='r1',extra={})=>m.createRound(state,{id,name:id,planId:'plan',createdAt:time,...extra});
function fixture() {
  let state=m.importPlan(m.empty(),plan()); state=round(state);
  state=m.registerEnvironment(state,environment('a'));state=m.attachEnvironment(state,'r1','a');return state;
}
const observation=(id,caseId='constructor',env='a',status='passed',executedAt=time)=>({id,caseId,environmentId:env,environment:environment(env),status,executedAt,recordedAt:time,tester:'Tester',notes:'Observed outcome',evidence:'local evidence'});
function rejectsUnchanged(state,action,pattern) {
  const snapshot=structuredClone(state); assert.throws(()=>action(state),pattern);assert.deepEqual(state,snapshot);
}

test('plan revision updates are explicit, identity-bound and idempotent',()=>{
  let state=m.importPlan(m.empty(),plan());assert.equal(m.importPlan(state,plan()),state);
  rejectsUnchanged(state,s=>m.importPlan(s,{...plan(),title:'Changed'}),/revision/);
  rejectsUnchanged(state,s=>m.importPlan(s,{...plan(),revision:1,version:'other'}),/version/);
  state=m.importPlan(state,{...plan(),revision:1,title:'Updated'});
  assert.equal(state.plans[0].title,'Updated');rejectsUnchanged(state,s=>m.importPlan(s,plan()),/revision/);
});
test('empty diff still selects smoke after all previous cases passed, with frozen history',()=>{
  let state=fixture();state=m.recordBatch(state,'r1',plan().cases.map((item,i)=>observation(`o${i}`,item.id)));
  const previous=structuredClone(state.rounds[0]); state=round(state,'r2',{changedIds:[]});
  assert.deepEqual(state.rounds[1].cases.map(item=>item.id),['constructor']);assert.deepEqual(state.rounds[0],previous);
  assert.equal(m.statusOf(state.rounds[1],'constructor'),'untested');
});
test('prior failure precedes smoke and change cases, IDs including prototype keys are retained',()=>{
  let state=fixture();state=m.record(state,'r1',observation('failure','FAIL','a','failed'));
  state=round(state,'r2',{changedIds:['constructor','FAIL','CHANGE']});
  assert.deepEqual(state.rounds[1].cases.map(item=>item.id),['FAIL','constructor','CHANGE']);
  assert.deepEqual(state.rounds[1].cases[0].selectionReasons,['previous-failure','change']);
  assert.deepEqual(state.rounds[1].cases[1].selectionReasons,['smoke','change']);
});
test('edited case content and smoke labels persist into later rounds without altering snapshots',()=>{
  let state=fixture(); const old=structuredClone(state.rounds[0]);
  state=m.editCase(state,'plan',{...plan().cases[1],steps:'Updated regression steps',types:['smoke','functional']});
  state=round(state,'r2',{changedIds:[]});state=round(state,'r3',{changedIds:[]});
  assert.equal(state.rounds[2].cases.find(item=>item.id==='FAIL').steps,'Updated regression steps');assert.deepEqual(state.rounds[0],old);
  state=m.editCase(state,'plan',{...state.plans[0].cases.find(item=>item.id==='FAIL'),types:['functional']});
  state=round(state,'r4',{changedIds:[]});assert.deepEqual(state.rounds[3].cases.map(item=>item.id),['constructor']);
});
test('missing smoke, unknown changed IDs and duplicate round identities reject without mutation',()=>{
  let state=m.importPlan(m.empty(),{...plan(),cases:[caseOf('NO-SMOKE')]});
  rejectsUnchanged(state,s=>round(s),/smoke/);state=fixture();
  rejectsUnchanged(state,s=>round(s,'r2',{changedIds:['missing']}),/Changed case/);
  rejectsUnchanged(state,s=>round(s),/already exists/);
});
test('single and batch saves require a registered round environment, valid status, tester and time',()=>{
  const state=fixture();
  const invalid=[{...observation('x'),environmentId:'missing'}, {...observation('x'),environment:{...environment('a'),configuration:'Changed'}}, {...observation('x'),status:'invented'}, {...observation('x'),executedAt:'yesterday'}, {...observation('x'),executedAt:'2026-02-31T04:00:00Z'}, {...observation('x'),tester:''}, {...observation('x'),caseId:'missing'}];
  for(const item of invalid) {
    rejectsUnchanged(state,s=>m.record(s,'r1',item));
    rejectsUnchanged(state,s=>m.recordBatch(s,'r1',[observation('good'),item]));
  }
  const withB=m.registerEnvironment(state,environment('b'));
  rejectsUnchanged(withB,s=>m.record(s,'r1',observation('x','constructor','b')),/Round environment/);
  rejectsUnchanged(state,s=>m.recordBatch(s,'r1',[]),/at least one/);
});
test('environment attachment and repeated archive imports are idempotent',()=>{
  const state=fixture();assert.equal(m.attachEnvironment(state,'r1','a'),state);
  assert.equal(m.importArchive(state,structuredClone(state)),state);
  rejectsUnchanged(state,s=>m.registerEnvironment(s,environment('a')),/registered/);
  rejectsUnchanged(state,s=>m.attachEnvironment(s,'r1','missing'),/Environment/);
});
test('same-model environments stay distinct; another pass cannot clear a failure',()=>{
  let state=fixture();state=m.registerEnvironment(state,environment('b'));state=m.attachEnvironment(state,'r1','b');
  state=m.record(state,'r1',observation('a-fail','constructor','a','failed'));
  state=m.record(state,'r1',observation('b-pass','constructor','b','passed'));
  assert.equal(m.statusOf(state.rounds[0],'constructor'),'failed');
  state=m.record(state,'r1',observation('a-pass','constructor','a','passed','2026-10-22T04:01:00Z'));
  assert.equal(m.statusOf(state.rounds[0],'constructor'),'passed');
  state=m.record(state,'r1',observation('older-fail','constructor','a','failed','2026-10-22T03:59:00Z'));
  assert.equal(m.statusOf(state.rounds[0],'constructor'),'passed');assert.equal(state.rounds[0].observations.length,4);
});
test('archive restores registered environments and history; later observations merge without replacement',()=>{
  const base=fixture();let incoming=m.record(base,'r1',observation('o1'));
  let restored=m.importArchive(m.empty(),JSON.parse(JSON.stringify(incoming)));
  assert.deepEqual(restored.rounds,incoming.rounds);assert.deepEqual(restored.environments,incoming.environments);
  incoming=m.record(incoming,'r1',observation('o2','FAIL','a','failed'));
  restored=m.importArchive(restored,incoming);assert.equal(restored.rounds[0].observations.length,2);
  assert.equal(m.importArchive(restored,incoming),restored);
});
test('summary uses execution then recording time; import order cannot clear a tied failure',()=>{
  let state=fixture();
  state=m.record(state,'r1',{...observation('newer-pass'),recordedAt:'2026-10-22T04:02:00Z'});
  state=m.record(state,'r1',{...observation('old-failure','constructor','a','failed'),recordedAt:'2026-10-22T04:01:00Z'});
  assert.equal(m.statusOf(state.rounds[0],'constructor'),'passed');
  state=m.record(state,'r1',{...observation('tie-failure','constructor','a','failed'),recordedAt:'2026-10-22T04:02:00Z'});
  assert.equal(m.statusOf(state.rounds[0],'constructor'),'failed');
  const reversed={...state.rounds[0],observations:[...state.rounds[0].observations].reverse()};
  assert.equal(m.statusOf(reversed,'constructor'),'failed');
});
test('an older round imported last does not replace the most recent round for preparation',()=>{
  let state=fixture();state=m.record(state,'r1',observation('old-fail','FAIL','a','failed'));
  state=round(state,'r2',{createdAt:'2026-10-22T04:05:00Z'});state=m.attachEnvironment(state,'r2','a');
  state=m.recordBatch(state,'r2',[observation('fixed','FAIL','a','passed'),observation('smoke')]);
  const old={...structuredClone(state.rounds[0]),id:'imported-older',createdAt:'2026-10-22T03:00:00Z'};
  state=m.importArchive(state,{...structuredClone(state),rounds:[old]});
  state=round(state,'r3',{createdAt:'2026-10-22T04:10:00Z',changedIds:[]});
  assert.deepEqual(state.rounds.at(-1).cases.map(item=>item.id),['constructor']);
});
test('conflicting historical definitions, observations and environments reject the whole import',()=>{
  const state=m.record(fixture(),'r1',observation('o1'));
  const edits=[archive=>archive.rounds[0].cases[0].steps='rewritten',archive=>archive.rounds[0].observations[0].notes='rewritten',archive=>archive.environments[0].label='rewritten'];
  for(const edit of edits){const incoming=structuredClone(state);edit(incoming);rejectsUnchanged(state,s=>m.importArchive(s,incoming));}
  const invalid=structuredClone(state);invalid.rounds.push({...structuredClone(invalid.rounds[0]),id:'invalid',observations:[observation('invalid','missing')]});
  rejectsUnchanged(state,s=>m.importArchive(s,invalid),/Case/);
  rejectsUnchanged(state,s=>m.importArchive(s,{...invalid,schemaVersion:99}),/schema/);
});
test('JSON data round-trips hostile-looking text as data and rejects duplicate IDs/types',()=>{
  const input=plan();input.cases[0].title='<img src=x onerror=alert(1)>';input.cases.push(caseOf('toString',['functional']));
  let state=m.importPlan(m.empty(),input);state=round(state);
  assert.equal(state.rounds[0].cases.length,4);assert.deepEqual(m.validate(JSON.parse(JSON.stringify(state))),state);
  rejectsUnchanged(state,s=>m.importPlan(s,{...input,revision:1,cases:[input.cases[0],input.cases[0]]}),/duplicate/);
  assert.throws(()=>m.validatePlan({...input,cases:[{...input.cases[0],types:['smoke','smoke']}]}),/types/);
});
test('one invalid batch observation cannot partially append good observations',()=>{
  const state=fixture();rejectsUnchanged(state,s=>m.recordBatch(s,'r1',[observation('good'),observation('bad','missing')]),/Case/);
  const result=m.recordBatch(state,'r1',[observation('one'),observation('two','FAIL')]);
  assert.equal(result.rounds[0].observations.length,2);assert.equal(state.rounds[0].observations.length,0);
  rejectsUnchanged(result,s=>m.record(s,'r1',observation('one')),/already exists/);
});
