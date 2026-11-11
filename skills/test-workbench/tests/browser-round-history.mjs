import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import {createWorkbenchServer} from '../scripts/workbench-server.mjs';
import {FakeGitHub} from './fake-github.mjs';
import * as model from '../assets/workbench/model.mjs';

const {chromium}=createRequire(import.meta.url)(process.env.TESTFLOW_PLAYWRIGHT_MODULE??'playwright');
const at='2026-11-10T00:00:00Z',actor='Fixture';
const environment={id:'env',label:'Browser',kind:'browser',configuration:'Fixture'};
const item=id=>({id,title:id,types:['smoke'],priority:'P1',preconditions:'',steps:'Execute',expected:'Observe'});
const cases=[item('A'),{...item('B'),dependsOn:['A']}];
let state=model.registerEnvironment(model.empty(),environment);
function round(id,createdAt,pr,revision){
  state=model.importPlan(state,{id:'p',revision,title:'Shared plan',version:'2.0.0',source:'sha-'+id,build:id,pr,cases});
  state=model.createRound(state,{id,planId:'p',name:id,createdAt,selection:{source:'issue',planRevision:revision,cases:['B']}});
}
function result(id,status){
  state=model.attachEnvironment(state,id,environment.id);
  for(const [action,from] of [['prepare','draft'],['begin','ready']])state=model.transitionRound(state,id,{id:action,from,action,actor,at});
  for(const caseId of ['A','B']){
    state=model.startExecution(state,id,{id:'start-'+caseId,caseId,environmentId:environment.id,from:'untested',actor,at});
    state=model.record(state,id,{id:'record-'+caseId,caseId,environmentId:environment.id,environment,status:caseId==='A'?'passed':status,executedAt:at,recordedAt:at,tester:actor,notes:'Fixture',evidence:'Evidence'});
  }
  state=model.transitionRound(state,id,{id:'complete',from:'running',action:'complete',actor,at});
}
round('first','2026-11-10T09:00:00+08:00','PR-1',0);result('first','failed');
round('third','2026-11-10T03:00:00Z','PR-1',1);result('third','passed');
round('second','2026-11-10T02:00:00Z','PR-1',2);result('second','partial');
round('single','2026-11-10T04:00:00Z','PR-2',3);
state.revision=1;
const api=new FakeGitHub(),source=api.source();
await source.initialize();await source.write(0,state);
const app=await createWorkbenchServer({source});
const browser=await chromium.launch({headless:true,...(process.env.TESTFLOW_CHROME?{executablePath:process.env.TESTFLOW_CHROME}:{})});
try{
  const page=await browser.newPage(),history=page.locator('#round-history'),summary=page.locator('#test-conclusion');
  await page.goto(app.url+'#plan=p&round=first&view=summary');
  await history.getByText(/最新轮次：通过/).waitFor();
  assert.match(await history.textContent(),/sha-third.*覆盖：A, B · 1 个环境/s);
  assert.match(await summary.textContent(),/本轮测试结论：未通过/);
  assert.match(await history.locator('[aria-current]').textContent(),/first/);
  const options=await page.locator('#round optgroup[label="PR-1"] option').allTextContents();
  assert.match(options[0],/第 1 轮.*first.*→/);
  assert.match(options[1],/第 2 轮.*second.*→/);
  assert.match(options[2],/第 3 轮.*third.*最新/);
  assert.equal(await page.locator('#round optgroup[label="PR-2"] option').textContent(),'single');
  await history.getByRole('link',{name:/second/}).click();
  await summary.getByText(/本轮测试结论：部分执行/).waitFor();
  assert.match(page.url(),/round=second/);
  assert.deepEqual((await source.read()).state,state);
  let updated=model.transitionRound(state,'third',{id:'reopen',action:'reopen',from:'completed',actor,at,reason:'Retest prerequisite'});
  updated=model.startExecution(updated,'third',{id:'restart-A',caseId:'A',environmentId:environment.id,from:'passed',actor,at});
  updated.revision=2;
  await source.write(1,updated);
  await page.locator('#reload').click();
  await history.getByText(/结论证据已过期/).waitFor();
  assert.match(await summary.textContent(),/本轮测试结论：部分执行/);
  await history.getByRole('link',{name:/first/}).click();
  await summary.getByText(/本轮测试结论：未通过/).waitFor();
  assert.match(page.url(),/round=first/);
  assert.deepEqual((await source.read()).state,updated);
  console.log('PASS: zoned order, independent old links and verdicts, latest frozen scope and stale evidence');
}finally{await browser.close();await app.close();}
