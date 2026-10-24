import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
const at='2026-10-22T10:00:00Z';
const item=(id,types=['functional'])=>({id,title:`Test ${id}`,priority:'P0',types,preconditions:'Fixture prerequisite',steps:`Execute ${id}`,expected:`Expected ${id}`});
const next=()=>({passed:{action:'test',caseId:'SESSION',reason:'Verify session persists'},failed:{action:'test',caseId:'DIAG',reason:'Collect login failure diagnostics'},partial:{action:'retry',caseId:'LOGIN',reason:'Complete unverified login checks; retain prior evidence'},blocked:{action:'wait',reason:'Restore account/network prerequisite before retesting',resumeWhen:'A valid account and reachable test service are available'},skipped:{action:'test',caseId:'OFFLINE',reason:'Continue independent offline coverage'}});
const plan=()=>({id:'p',revision:0,version:'v',title:'Routing fixture',source:'sha',build:'',pr:'',cases:[{...item('LOGIN',['smoke']),next:next()},item('SESSION'),item('DIAG'),item('OFFLINE')]});
const environment=id=>({id,label:id,kind:'browser',configuration:'isolated'});
function fixture(){let s=m.importPlan(m.empty(),plan());s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});s=m.registerEnvironment(s,environment('e'));s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});return m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});}
const start=(s,caseId='LOGIN',environmentId='e',suffix='')=>m.startExecution(s,'r',{id:`start-${caseId}-${environmentId}${suffix}`,caseId,environmentId,actor:'Tester',at,from:m.executionState(s.rounds[0],caseId,environmentId)});
const observation=(id,status,extra={})=>({id,caseId:'LOGIN',environmentId:'e',environment:environment('e'),status,tester:'Tester',executedAt:at,recordedAt:at,notes:'Observed evidence; completed input check, remaining session check',evidence:'fixture screenshot',...extra});
function rejects(state,fn,pattern){const before=structuredClone(state);assert.throws(()=>fn(state),pattern);assert.deepEqual(state,before);}

test('each outcome selects an explicit concrete next test or wait with source evidence',()=>{
  for(const status of m.RESULTS) {
    const s=m.record(start(fixture()),'r',observation(`o-${status}`,status)),before=structuredClone(s),advice=m.nextTest(s.rounds[0],'LOGIN','e');
    assert.equal(advice.action,next()[status].action);assert.equal(advice.targetCaseId,next()[status].caseId??null);assert.equal(advice.basedOnObservationId,`o-${status}`);assert.equal(advice.state,status);assert.equal(advice.environmentId,'e');
    if(advice.target){assert.equal(advice.target.steps,`Execute ${advice.target.id}`);assert.equal(advice.target.expected,`Expected ${advice.target.id}`);}else assert.equal(advice.available,false);
    assert.deepEqual(m.exportAI(s).projection.rounds[0].executions.find(entry=>entry.caseId==='LOGIN').nextTest,advice);assert.deepEqual(s,before);
    if(advice.target)advice.target.steps='Mutated copy';assert.deepEqual(s,before);
  }
});

test('invalid or incomplete routing rejects plan import/edit/archive before mutation',()=>{
  const s=fixture();const bads=[n=>delete n.failed,n=>n.unknown={action:'done',reason:'typo'},n=>n.passed.action='invented',n=>n.passed.reason='',n=>n.passed.caseId='missing',n=>n.partial.caseId='DIAG',n=>n.blocked.caseId='hidden',n=>n.skipped=null,n=>delete n.blocked.resumeWhen,n=>n.passed.environmentId='other',n=>n.failed.unresolvedFailureId=null,n=>n.partial.state='passed'];
  for(const change of bads){const p=plan();change(p.cases[0].next);p.revision=1;rejects(s,x=>m.importPlan(x,p));rejects(s,x=>m.editCase(x,'p',p.cases[0]));const incoming=structuredClone(s);incoming.plans[0]=p;rejects(s,x=>m.importArchive(x,incoming));}
  rejects(s,x=>m.importPlan(x,{...plan(),revision:1,cases:[{...plan().cases[0],next:null}]}));
  const bad=structuredClone(s);bad.rounds[0].cases[0].next.failed.caseId='missing';rejects(s,x=>m.importArchive(x,bad),/Next case not found/);
});

test('reachable targets freeze recursively, cycles terminate and new rounds do not infer outcomes',()=>{
  const p=plan();p.cases[1].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:'LOGIN',reason:'Review original login again'}]));
  let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});
  assert.deepEqual(s.rounds[0].cases.map(entry=>entry.id),['LOGIN','SESSION','DIAG','OFFLINE']);assert(s.rounds[0].cases[0].selectionReasons.includes('smoke'));
  assert(s.rounds[0].cases.slice(1).every(entry=>entry.selectionReasons.includes('conditional-next')));assert.equal(s.rounds[0].observations.length,0);assert.equal(s.rounds[0].workflow.events.length,0);
  const original=structuredClone(s.rounds[0]);s=m.editCase(s,'p',{...p.cases[1],steps:'New session procedure'});assert.deepEqual(s.rounds[0],original);
  s=m.createRound(s,{id:'r2',planId:'p',name:'Round 2',createdAt:at,changedIds:[]});assert.equal(s.rounds[1].cases.find(entry=>entry.id==='SESSION').steps,'New session procedure');
});

test('diagnostic and another environment passing never clear original failure or change its branch',()=>{
  let s=m.importPlan(m.empty(),plan());s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});
  for(const id of ['e','f']){s=m.registerEnvironment(s,environment(id));s=m.attachEnvironment(s,'r',id);}s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});s=m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});
  s=m.record(start(s),'r',observation('failure','failed'));s=m.record(start(s,'DIAG'),'r',observation('diag-pass','passed',{caseId:'DIAG'}));s=m.record(start(s,'LOGIN','f'),'r',observation('other-pass','passed',{environmentId:'f',environment:environment('f')}));
  assert.equal(m.statusOf(s.rounds[0],'LOGIN'),'failed');assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').targetCaseId,'DIAG');assert.equal(m.nextTest(s.rounds[0],'LOGIN','f').targetCaseId,'SESSION');
  s=m.record(start(s,'LOGIN','e','retry'),'r',observation('fixed','passed'));assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').targetCaseId,'SESSION');assert.equal(s.rounds[0].observations.length,4);
});

test('flat cases explicitly lack routing; current/closed/unknown contexts do not invent a branch',()=>{
  let s=fixture();assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').action,'current');s=start(s);assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').action,'current');
  s=m.record(s,'r',observation('pass','passed'));s=m.record(start(s,'DIAG'),'r',observation('diag','passed',{caseId:'DIAG'}));assert.equal(m.nextTest(s.rounds[0],'DIAG','e').action,'unconfigured');
  assert.throws(()=>m.nextTest(s.rounds[0],'missing','e'),/case/);assert.throws(()=>m.nextTest(s.rounds[0],'LOGIN','missing'),/environment/);
  for(const caseId of ['SESSION','OFFLINE'])s=m.record(start(s,caseId),'r',observation(caseId,'skipped',{caseId}));
  s=m.transitionRound(s,'r',{id:'end',action:'complete',from:'running',actor:'Tester',at});assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').available,false);
});

test('routed partial requires completed/unverified explanation; flat historical partial stays readable',()=>{
  const s=start(fixture());rejects(s,x=>m.record(x,'r',observation('partial','partial',{notes:''})),/requires notes/);
  rejects(s,x=>m.recordBatch(x,'r',[observation('partial','partial',{notes:''})]),/requires notes/);
  const incoming=structuredClone(s);incoming.rounds[0].observations.push(observation('bad','partial',{notes:''}));incoming.rounds[0].workflow.events.push({id:'result:bad',scope:'execution',action:'record',from:'running',to:'partial',actor:'Tester',at,reason:'',caseId:'LOGIN',environmentId:'e',observationId:'bad'});rejects(s,x=>m.importArchive(x,incoming),/requires notes/);
  const flat=structuredClone(s);delete flat.plans[0].cases[0].next;delete flat.rounds[0].cases[0].next;
  const result=m.record(flat,'r',observation('old','partial',{notes:''}));assert.equal(m.nextTest(result.rounds[0],'LOGIN','e').action,'unconfigured');assert.equal(m.importArchive(result,result),result);
});

test('partial, blocking or skipping a retest cannot clear a known failure',()=>{
  for(const routed of [true,false]) {
  const base=fixture();if(!routed){delete base.plans[0].cases[0].next;delete base.rounds[0].cases[0].next;}
  let s=m.record(start(base),'r',observation('known-failure','failed'));
  for(const status of ['partial','blocked','skipped']) {
    s=start(s,'LOGIN','e',status);assert.equal(m.statusOf(s.rounds[0],'LOGIN'),'failed');
    s=m.record(s,'r',observation(`retest-${status}`,status));assert.equal(m.statusOf(s.rounds[0],'LOGIN'),'failed');
    const advice=m.nextTest(s.rounds[0],'LOGIN','e');assert.equal(advice.state,status);assert.equal(advice.unresolvedFailureId,'known-failure');
  }
  const later=m.createRound(s,{id:'after-skip',planId:'p',name:'Failure retained',createdAt:at,changedIds:[]});assert(later.rounds.at(-1).cases.find(item=>item.id==='LOGIN').selectionReasons.includes('previous-failure'));
  s=m.record(start(s,'LOGIN','e','actual-fix'),'r',observation('verified-fix','passed'));
  assert.equal(m.statusOf(s.rounds[0],'LOGIN'),'passed');assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').unresolvedFailureId,null);assert.equal(s.rounds[0].observations.length,5);
  }
});

test('done and missing routes stay explicit; unvisited branches require deliberate outcomes',()=>{
  const p=plan();p.cases[0].next.passed={action:'done',reason:'Required login scope is complete'};
  let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});s=m.registerEnvironment(s,environment('e'));s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});s=m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});
  s=m.record(start(s),'r',observation('pass','passed'));const advice=m.nextTest(s.rounds[0],'LOGIN','e');assert.equal(advice.action,'done');assert.equal(advice.target,null);
  assert.equal(m.importArchive(s,structuredClone(s)),s);assert.equal(m.statusOf(s.rounds[0],'DIAG'),'untested');
  rejects(s,x=>m.transitionRound(x,'r',{id:'end',action:'complete',from:'running',actor:'Tester',at}),/unfinished/);
});

test('branches with prototype-looking IDs are data; removed failed cases retain reachable historical targets',()=>{
  const p=plan();p.cases[1].id='constructor';p.cases[0].next.passed.caseId='constructor';
  let s=m.importPlan(m.empty(),p);s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at,changedIds:[]});assert(s.rounds[0].cases.some(entry=>entry.id==='constructor'));
  s=m.registerEnvironment(s,environment('e'));s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Tester',at});s=m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Tester',at});s=m.record(start(s),'r',observation('failed','failed'));
  s=m.importPlan(s,{...p,revision:1,cases:[item('NEW',['smoke'])]});s=m.createRound(s,{id:'r2',planId:'p',name:'Round 2',createdAt:at,changedIds:[]});
  assert.deepEqual(s.rounds[1].cases.map(entry=>entry.id),['LOGIN','NEW','constructor','DIAG','OFFLINE']);assert.equal(m.statusOf(s.rounds[1],'LOGIN'),'untested');
});

test('pre-execution blocking/skipping records no fabricated start or execution time; failures still require execution',()=>{
  for(const status of ['blocked','skipped']) {
    const base=fixture(),before=structuredClone(base),initialEvents=base.rounds[0].workflow.events.length;
    const s=m.record(base,'r',observation(status,status,{executedAt:null}));
    assert.equal(s.rounds[0].workflow.events.length,initialEvents+1);assert.equal(s.rounds[0].workflow.events.at(-1).action,'defer');
    assert.equal(s.rounds[0].observations[0].executedAt,null);assert.equal(m.inspectWorkflow(s.rounds[0]).executions[0].attemptId,null);
    assert.equal(m.nextTest(s.rounds[0],'LOGIN','e').state,status);assert.deepEqual(base,before);assert.equal(m.importArchive(s,s),s);
    rejects(base,x=>m.record(x,'r',observation('invented-time',status)),/executedAt=null/);
    rejects(base,x=>m.record(x,'r',observation('missing-reason',status,{executedAt:null,notes:''})),/requires notes/);
    const forged=structuredClone(s);forged.rounds[0].workflow.events.at(-1).action='record';rejects(base,x=>m.importArchive(x,forged));
  }
  const base=fixture();for(const status of ['passed','failed','partial'])rejects(base,x=>m.record(x,'r',observation('not-run',status,{executedAt:null})));
  const actions=m.exportAI(base).projection.rounds[0].executions[0].nextActions;assert.deepEqual(actions.filter(entry=>entry.action==='defer').map(entry=>entry.to),['blocked','skipped']);
  rejects(base,x=>m.recordBatch(x,'r',[observation('skip','skipped',{executedAt:null}),observation('bad','failed',{caseId:'DIAG',executedAt:null})]));
});
