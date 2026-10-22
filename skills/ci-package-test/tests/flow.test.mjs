import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
import {locationHint,formatTestLocation} from '../assets/workbench/test-location.mjs';
const at='2026-10-22T12:00:00Z',env=id=>({id,label:id,kind:'mobile',configuration:'Disposable fixture'});
const location=()=>({app:'example.app',screen:'Login fixture',entryPath:['Open fixture app','Open login'],targets:[{name:'Login',by:'resource-id',value:'example.app:id/login',action:'Tap after confirming the current screen'}],verify:'Confirm the fixture page and selected device'});
const item=(id,dependsOn=[])=>({id,title:`Fixture ${id}`,priority:'P0',types:id==='LOGIN'?['smoke']:['functional'],preconditions:'Fixture',steps:`Execute ${id}`,expected:`Expected ${id}`,dependsOn});
const plan=()=>({id:'p',revision:0,version:'fixture',title:'Flow fixture',source:'fixture-sha',build:'',pr:'',cases:[{...item('LOGIN'),testLocation:location(),next:{passed:{action:'test',caseId:'PAY',reason:'Payment after login'},failed:{action:'retry',caseId:'LOGIN',reason:'Retest with original evidence'},partial:{action:'retry',caseId:'LOGIN',reason:'Complete remaining checks'},blocked:{action:'wait',reason:'Restore prerequisite',resumeWhen:'Fixture service available'},skipped:{action:'done',reason:'End this branch only'}}},item('CART'),item('PAY',['LOGIN','CART'])]});
function fixture(){let s=m.importPlan(m.empty(),plan());s=m.createRound(s,{id:'r',planId:'p',name:'Flow fixture',createdAt:at,changedIds:[]});for(const id of ['e','f']){s=m.registerEnvironment(s,env(id));s=m.attachEnvironment(s,'r',id);}s=m.transitionRound(s,'r',{id:'ready',action:'prepare',from:'draft',actor:'Fixture',at});return m.transitionRound(s,'r',{id:'run',action:'begin',from:'ready',actor:'Fixture',at});}
const start=(s,id,environmentId='e',suffix='')=>m.startExecution(s,'r',{id:`start-${id}-${environmentId}${suffix}`,caseId:id,environmentId,from:m.executionState(s.rounds[0],id,environmentId),actor:'Fixture',at});
function result(s,id,status='passed',environmentId='e',suffix=''){return m.record(start(s,id,environmentId,suffix),'r',{id:`result-${id}-${environmentId}${suffix}`,caseId:id,environmentId,environment:env(environmentId),status,tester:'Fixture',executedAt:at,recordedAt:at,notes:'Fixture actual observation',evidence:'Fixture evidence'});}
const flow=(s,id='LOGIN',environmentId='e')=>m.projectFlow(s.rounds[0],{caseId:id,environmentId});
function rejects(s,fn){const before=structuredClone(s);assert.throws(()=>fn(s));assert.deepEqual(s,before);}

test('graph distinguishes dependency and grouped next edges, cycles terminate and projection is read-only',()=>{
  const s=fixture(),before=structuredClone(s),graph=flow(s);
  assert.equal(graph.nodes.length,3);assert.equal(graph.edges.filter(edge=>edge.kind==='dependency').length,2);
  assert.deepEqual(graph.edges.find(edge=>edge.kind==='next'&&edge.to==='LOGIN').outcomes,['failed','partial']);
  const positions=new Set(graph.nodes.map(node=>`${node.x},${node.y}`));assert.equal(positions.size,3);
  for(const edge of graph.edges.filter(edge=>edge.kind==='dependency'))assert(graph.nodes.find(n=>n.caseId===edge.from).x<graph.nodes.find(n=>n.caseId===edge.to).x);
  assert.deepEqual(graph.nextTest,m.nextTest(s.rounds[0],'LOGIN','e'));assert.deepEqual(s,before);
  graph.nodes[0].testLocation.targets[0].value='changed';assert.deepEqual(s,before);
});

test('graph scopes readiness and concrete next hints to one environment and never invents state without selection',()=>{
  let s=result(fixture(),'LOGIN');assert.equal(flow(s).nextTest.targetCaseId,'CART');
  assert.equal(flow(s).nodes.find(n=>n.caseId==='PAY').dependenciesSatisfied,false);
  s=result(s,'CART','passed','f');assert.equal(flow(s).nextTest.targetCaseId,'CART');
  s=result(s,'CART');assert.equal(flow(s).nextTest.targetCaseId,'PAY');assert(flow(s).edges.some(edge=>edge.kind==='next'&&edge.to==='PAY'&&edge.active));
  assert.equal(flow(s,'LOGIN','f').nextTest.action,'current');
  for(const id of ['','unknown']){const missing=flow(s,'LOGIN',id);assert.equal(missing.mode,'environment-required');assert(missing.nodes.every(node=>node.state===null));assert.equal(missing.nextTest,null);}
  assert.equal(m.projectFlow(plan()).mode,'definition');
  const legacy=structuredClone(s.rounds[0]);delete legacy.workflow;assert.equal(m.projectFlow(legacy).mode,'legacy');assert(m.projectFlow(legacy).nodes.every(node=>node.state===null));
});

test('graph retains unresolved failure, stale evidence, wait/done and frozen round hints',()=>{
  for(const status of ['failed','partial','blocked','skipped']){const s=result(fixture(),'LOGIN',status),g=flow(s);assert.equal(g.nextTest.action,plan().cases[0].next[status].action);if(status==='failed')assert(g.nodes[0].unresolvedFailureId);if(status==='blocked')assert(g.nextTest.resumeWhen);}
  let s=fixture();for(const id of ['LOGIN','CART','PAY'])s=result(s,id);s=result(s,'LOGIN','passed','e','new');
  assert(flow(s).nodes.find(n=>n.caseId==='PAY').dependencyStale);assert.equal(flow(s,'PAY').nextTest.action,'retry');
  const snapshot=structuredClone(s.rounds[0]);s=m.editCase(s,'p',{...s.plans[0].cases[0],testLocation:{screen:'Updated current library'}});
  assert.deepEqual(s.rounds[0],snapshot);assert.equal(flow(s).nodes[0].testLocation.screen,'Login fixture');
});

test('test-location validation guards edit/import/round/archive before any state mutation',()=>{
  const s=fixture();const bads=[null,{},[],{screen:''},{screen:'X',app:3},{screen:'X',entryPath:'path'},{screen:'X',entryPath:['ok',null]},{screen:'X',verify:''},{screen:'X',targets:null},{screen:'X',targets:[{name:'X',by:'coordinates',value:'0,0',action:'tap'}]},{screen:'X',targets:[{name:'X',by:'text',value:'X',action:'tap'},{name:'bad'}]},{screen:'X',targets:[{name:'X',by:'text',value:'X',action:'tap',environmentId:'forged'}]},{screen:'X',verified:true}];
  for(const bad of bads){const p=plan();p.revision=1;p.cases[0].testLocation=bad;rejects(s,x=>m.importPlan(x,p));rejects(s,x=>m.editCase(x,'p',p.cases[0]));const archive=structuredClone(s);archive.rounds[0].cases[0].testLocation=bad;rejects(s,x=>m.importArchive(x,archive));}
  const corrupt=structuredClone(s);corrupt.plans[0].cases[0].testLocation={screen:'X',targets:[{}]};rejects(corrupt,x=>m.attachEnvironment(x,'r','e'));rejects(corrupt,x=>m.createRound(x,{id:'r2',planId:'p',name:'Reject malformed metadata',createdAt:at,changedIds:[]}));rejects(corrupt,x=>start(x,'LOGIN'));
  const valid=m.editCase(s,'p',{...s.plans[0].cases[0],testLocation:{screen:'X'}});assert.equal(valid.plans[0].cases[0].testLocation.screen,'X');assert.equal(m.importArchive(valid,valid),valid);
});

test('hints survive archives and annotation snapshots; missing hints remain valid and unverified',()=>{
  let s=fixture();s=m.addAnnotation(s,{id:'note',planId:'p',roundId:'r',caseId:'LOGIN',target:{field:'steps',quote:''},event:{id:'note-first',kind:'comment',author:'Fixture',body:'Verify location',createdAt:at}});
  s=m.importArchive(m.empty(),JSON.parse(JSON.stringify(s)));assert.equal(s.annotations[0].context.case.testLocation.screen,'Login fixture');
  const malformed=structuredClone(s);malformed.annotations[0].context.case.testLocation.targets[0].by='unknown';rejects(s,x=>m.importArchive(x,malformed));
  const snapshot=m.exportAI(s);assert.equal(snapshot.contract.testLocation.field,'case.testLocation');assert.equal(snapshot.projection.rounds[0].executions[0].testLocation.verification,'unverified-live-screen');
  assert.deepEqual(snapshot.projection.rounds[0].flows[0],m.projectFlow(s.rounds[0],{environmentId:'e'}));
  const old=plan();delete old.cases[0].testLocation;assert(m.importPlan(m.empty(),old));assert.equal(locationHint(old.cases[0]).available,false);
});

test('phone handoff binds source/round/environment and declared selectors without claiming live verification',()=>{
  const current=plan().cases[0],copy=structuredClone(current);
  const text=formatTestLocation(current,{version:'fixture-v',source:'fixture-sha',build:'fixture-build',planId:'p',roundId:'r',environmentId:'e',environment:env('e'),state:'untested',unresolvedFailureId:'known-failure',dependencyStale:true,unmetDependencies:[{caseId:'DEP',state:'failed'}]});
  for(const token of ['fixture-v','fixture-sha','fixture-build','p / r / e','Disposable fixture','known-failure','DEP (failed)','旧结果需要重新验证','LOGIN','example.app:id/login','Execute LOGIN','Expected LOGIN','未核对当前设备界面','不要凭旧坐标'])assert(text.includes(token),token);
  assert.deepEqual(current,copy);assert(formatTestLocation(item('NOHINT'),{version:'v',source:'sha',planId:'p'}).includes('尚未配置'));
});

test('completed rounds keep graph evidence but expose no currently executable route',()=>{
  let s=fixture();for(const environmentId of ['e','f'])for(const id of ['LOGIN','CART','PAY'])s=result(s,id,'passed',environmentId);
  s=m.transitionRound(s,'r',{id:'completed',action:'complete',from:'running',actor:'Fixture',at});
  const graph=flow(s);assert.equal(graph.nextTest.available,false);assert(graph.edges.every(edge=>!edge.active));assert(graph.nodes.every(node=>node.validPass));
});
