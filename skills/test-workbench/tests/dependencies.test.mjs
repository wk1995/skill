import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
const at='2026-10-22T12:00:00Z';
const env=id=>({id,label:id,kind:'browser',configuration:'Fixture'});
const item=(id,dependsOn=[])=>({id,title:id,priority:'P0',types:id==='PAY'?['smoke']:['functional'],preconditions:'Fixture',steps:`Execute ${id}`,expected:`Expected ${id}`,dependsOn});
const plan=()=>({id:'p',version:'v',revision:0,title:'Dependencies',source:'sha',build:'',pr:'',cases:[item('PAY',['CART']),item('CART',['LOGIN']),item('LOGIN')]});
const round=s=>s.rounds[0];
function fixture(ids=['e','f']){let s=m.importPlan(m.empty(),plan());s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});for(const id of ids){s=m.registerEnvironment(s,env(id));s=m.attachEnvironment(s,'r',id);}s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});return m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});}
const start=(s,caseId,environmentId='e',suffix='')=>m.startExecution(s,'r',{id:`start-${caseId}-${environmentId}${suffix}`,caseId,environmentId,from:m.executionState(round(s),caseId,environmentId),actor:'Tester',at});
const obs=(id,caseId,status='passed',environmentId='e',extra={})=>({id,caseId,status,environmentId,environment:env(environmentId),executedAt:at,recordedAt:at,tester:'Tester',notes:'Observed fixture',evidence:'Fixture evidence',...extra});
const pass=(s,id,env='e',suffix='')=>m.record(start(s,id,env,suffix),'r',obs(`${id}-${env}${suffix}`,id,'passed',env));
function rejects(s,fn,pattern){const before=structuredClone(s);assert.throws(()=>fn(s),pattern);assert.deepEqual(s,before);}

test('dependency graphs validate every writer, reject missing/self/duplicate/cyclic targets and allow next cycles',()=>{
  const base=fixture();
  const edits=[cases=>cases[0].dependsOn='LOGIN',cases=>cases[0].dependsOn=['PAY'],cases=>cases[0].dependsOn=['missing'],cases=>cases[0].dependsOn=['CART','CART'],cases=>cases[2].dependsOn=['PAY']];
  for(const edit of edits){const p=plan();p.revision=1;edit(p.cases);rejects(base,s=>m.importPlan(s,p));for(const changed of p.cases.filter((item,index)=>JSON.stringify(item)!==JSON.stringify(plan().cases[index])))rejects(base,s=>m.editCase(s,'p',changed));const archive=structuredClone(base);archive.plans[0]=p;rejects(base,s=>m.importArchive(s,archive));}
  rejects(base,s=>m.editCase(s,'p',{...plan().cases[0],dependsOn:['missing']}),/Dependency/);
  const p=plan();p.cases[2].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:'PAY',reason:'Continue dependent payment'}]));
  let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});assert.deepEqual(round(s).cases.map(item=>item.id),['LOGIN','CART','PAY']);assert(round(s).cases[0].selectionReasons.includes('dependency'));
  const q=plan();q.cases[2].id='constructor';q.cases[1].dependsOn=['constructor'];let keyed=m.importPlan(m.empty(),q);keyed=m.createRound(keyed,{id:'keyed',planId:'p',name:'Prototype IDs are data',createdAt:at,changedIds:[]});assert.deepEqual(round(keyed).cases.map(item=>item.id),['constructor','CART','PAY']);
});

test('prerequisites require all passes in this round/environment; AI identifies the first actionable ancestor',()=>{
  let s=fixture();rejects(s,x=>start(x,'PAY'),/Prerequisites/);
  let guidance=m.nextTest(round(s),'PAY','e');assert.equal(guidance.action,'prerequisite');assert.equal(guidance.targetCaseId,'LOGIN');assert.equal(guidance.target.steps,'Execute LOGIN');
  s=pass(s,'LOGIN','f');rejects(s,x=>start(x,'CART','e'),/Prerequisites/);
  s=pass(s,'LOGIN');s=pass(s,'CART');s=start(s,'PAY');assert.equal(m.executionState(round(s),'PAY','e'),'running');
  const execution=m.inspectWorkflow(round(s)).executions.find(entry=>entry.caseId==='PAY'&&entry.environmentId==='e');assert.deepEqual(execution.dependencyEvidence,[{caseId:'CART',observationId:'CART-e'}]);
  s=m.createRound(s,{id:'r2',planId:'p',name:'Round 2',createdAt:at,changedIds:[]});assert.equal(m.inspectWorkflow(s.rounds[1]).executions.length,0);assert.equal(m.statusOf(s.rounds[1],'PAY'),'untested');
});

test('nonpasses do not unlock dependencies; explicit pre-execution blocked/skipped remains available',()=>{
  for(const status of ['failed','partial','blocked','skipped']){
    let s=fixture();s=m.record(start(s,'LOGIN'),'r',obs(`login-${status}`,'LOGIN',status));rejects(s,x=>start(x,'CART'),/Prerequisites/);
    const actions=m.exportAI(s).projection.rounds[0].executions.find(entry=>entry.caseId==='CART'&&entry.environmentId==='e').nextActions;assert(!actions.some(item=>item.action==='start'));assert(actions.some(item=>item.action==='defer'));
    s=m.record(s,'r',obs('blocked-cart','CART','blocked','e',{executedAt:null}));assert.equal(round(s).observations.at(-1).executedAt,null);
  }
});

test('upstream retest invalidates passes transitively without rewriting evidence and blocks stale completion',()=>{
  let s=fixture();for(const id of ['LOGIN','CART','PAY'])s=pass(s,id);const history=structuredClone(round(s).observations);
  s=start(s,'LOGIN','e','again');assert.equal(m.statusOf(round(s),'PAY'),'blocked');assert.equal(m.statusOf(round(s),'CART'),'blocked');
  s=m.record(s,'r',obs('LOGIN-e-new','LOGIN'));const view=m.inspectWorkflow(round(s)).executions;
  assert(view.find(entry=>entry.caseId==='CART'&&entry.environmentId==='e').dependencyStale);assert.equal(m.nextTest(round(s),'PAY','e').targetCaseId,'CART');assert.deepEqual(round(s).observations.slice(0,3),history);
  rejects(s,x=>start(x,'PAY','e','too-soon'),/Prerequisites/);
  s=pass(s,'CART','e','new');assert.equal(m.nextTest(round(s),'PAY','e').action,'retry');s=pass(s,'PAY','e','new');assert.equal(m.statusOf(round(s),'PAY'),'untested');
  // e has a current pass; f remains untested and cannot be covered by e.
  assert(m.inspectWorkflow(round(s)).executions.find(entry=>entry.caseId==='PAY'&&entry.environmentId==='e').validPass);
});

test('dependency changes during execution reject stale outcomes but allow explicit block and fresh retry',()=>{
  let s=pass(pass(fixture(),'LOGIN'),'CART');s=start(s,'PAY');s=pass(s,'LOGIN','e','again');
  for(const status of ['passed','failed','partial'])rejects(s,x=>m.record(x,'r',obs(`stale-${status}`,'PAY',status)),/Prerequisite evidence/);
  const actions=m.exportAI(s).projection.rounds[0].executions.find(entry=>entry.caseId==='PAY'&&entry.environmentId==='e').nextActions;assert.deepEqual(actions.map(item=>item.to),['blocked','skipped']);
  rejects(s,x=>m.recordBatch(x,'r',[obs('stale','PAY')]));s=m.record(s,'r',obs('stopped','PAY','blocked'));s=pass(s,'CART','e','fresh');s=pass(s,'PAY','e','fresh');
  assert(m.inspectWorkflow(round(s)).executions.find(entry=>entry.caseId==='PAY'&&entry.environmentId==='e').validPass);
});

test('forged start/import, batch start and malformed idempotent state reject atomically',()=>{
  const s=fixture();rejects(s,x=>m.startExecutionBatch(x,'r',[{id:'a',caseId:'LOGIN',environmentId:'e',from:'untested',actor:'Tester',at},{id:'b',caseId:'CART',environmentId:'e',from:'untested',actor:'Tester',at}]),/Prerequisites/);
  const forged=structuredClone(s);round(forged).workflow.events.push({id:'forged',scope:'execution',action:'start',from:'untested',to:'running',actor:'Tester',at,reason:'',caseId:'PAY',environmentId:'e',observationId:'',dependencyEvidence:[{caseId:'CART',observationId:'fake-pass'}]});rejects(s,x=>m.importArchive(x,forged),/Prerequisites/);
  const invalid=structuredClone(s);round(invalid).cases.find(item=>item.id==='LOGIN').dependsOn=['PAY'];rejects(invalid,x=>m.attachEnvironment(x,'r','e'),/cyclic/);
  const roundEdit=structuredClone(s);round(roundEdit).cases.find(item=>item.id==='PAY').dependsOn=[];rejects(s,x=>m.importArchive(x,roundEdit),/historical/);
});

test('all declared prerequisites are required and stale passes alone prevent completion',()=>{
  const p=plan();p.cases[0].dependsOn=['LOGIN','CART'];let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});s=m.registerEnvironment(s,env('e'));s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});s=m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});
  s=pass(s,'LOGIN');rejects(s,x=>start(x,'PAY'),/Prerequisites/);s=pass(s,'CART');s=pass(s,'PAY');s=pass(s,'LOGIN','e','changed');
  assert(m.inspectWorkflow(round(s)).executions.every(entry=>entry.state==='passed'));assert.equal(m.roundActions(round(s)).find(action=>action.action==='complete').allowed,false);
  rejects(s,x=>m.transitionRound(x,'r',{id:'complete',action:'complete',from:'running',actor:'Tester',at}),/unfinished/);
  s=pass(s,'CART','e','fresh');s=pass(s,'PAY','e','fresh');s=m.transitionRound(s,'r',{id:'complete',action:'complete',from:'running',actor:'Tester',at});assert.equal(m.inspectWorkflow(round(s)).state,'completed');
});

test('explicit skip/block branches can continue independent tests without forcing prerequisites',()=>{
  const p=plan();p.cases.push(item('INDEPENDENT'));p.cases[0].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:'INDEPENDENT',reason:'Continue independent scope'}]));
  let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});s=m.registerEnvironment(s,env('e'));s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});s=m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});
  const skipped=m.record(s,'r',obs('scope-skip','PAY','skipped','e',{executedAt:null}));assert.equal(m.nextTest(round(skipped),'PAY','e').targetCaseId,'INDEPENDENT');
  const blocked=m.record(s,'r',obs('dep-block','PAY','blocked','e',{executedAt:null}));assert.equal(m.nextTest(round(blocked),'PAY','e').targetCaseId,'INDEPENDENT');
});
