// Disposable real-browser coverage for the focused-round UI in both source modes.
import {createRequire} from 'node:module';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {FileSource,command} from '../scripts/workspace-sources.mjs';
import {createWorkbenchServer} from '../scripts/workbench-server.mjs';
import {FakeGitHub} from './fake-github.mjs';
import * as m from '../assets/workbench/model.mjs';
const {chromium}=createRequire(import.meta.url)(process.env.TESTFLOW_PLAYWRIGHT_MODULE??'playwright');
const browser=await chromium.launch({headless:true,...(process.env.TESTFLOW_CHROME?{executablePath:process.env.TESTFLOW_CHROME}:{})});
const root=await fs.mkdtemp(path.join(os.tmpdir(),'focused-browser-')),apps=[];
async function until(check){for(let i=0;i<300;i++){if(await check())return;await new Promise(r=>setTimeout(r,20));}throw new Error('Timed out');}
try{
 await command('git',['init','-q','-b','main',root]);for(const [key,value] of [['user.name','Fixture'],['user.email','fixture@example.invalid'],['commit.gpgsign','false'],['core.hooksPath',os.devnull]])await command('git',['-C',root,'config',key,value]);await fs.writeFile(path.join(root,'README'),'Disposable');await command('git',['-C',root,'add','README']);await command('git',['-C',root,'commit','-qm','Fixture']);
 for(const [mode,source] of [['github-issues',new FakeGitHub().source()],['repository-files',new FileSource({repoRoot:root})]]){
  await source.initialize();const cases=Array.from({length:49},(_,i)=>({id:`C${i+1}`,title:`Case ${i+1}`,types:i===48?['smoke']:['functional'],priority:'P1',preconditions:'',steps:'Exercise',expected:'Observe'}));
  for(let i=0;i<48;i++)cases[i].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:cases[i+1].id,reason:'Optional next'}]));
  await source.write(0,m.importPlan(m.empty(),{id:'p',revision:0,title:'Focused fixture',version:'fixture',source:'sha',build:'',pr:'',cases}));
  const app=await createWorkbenchServer({source});apps.push(app);const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(app.url);await page.locator('#detail h2').waitFor();await page.locator('#round-setup').evaluate(node=>node.open=true);
  const form=page.locator('#round-form');await form.locator('[name=name]').fill('Focused bug retest');assert(await form.locator('[name=confirmed]').isDisabled());
  await form.locator('[name=cases]').fill('C1,C2');await form.locator('[name=source]').selectOption('issue');const before=(await source.read()).state;
  await page.locator('#preview-round').click();assert((await page.locator('#round-preview').textContent()).includes('冻结 2'));assert((await page.locator('#round-preview').textContent()).includes('排除（47）'));assert.deepEqual((await source.read()).state,before);
  await form.locator('[name=confirmed]').check();await form.locator('[name=cases]').fill('C1');assert(await form.locator('[name=confirmed]').isDisabled());assert.equal(await form.locator('[name=confirmed]').isChecked(),false);
  await page.locator('#preview-round').click();await form.locator('[name=confirmed]').check();await form.locator('button[type=submit]').click();await until(async()=>(await source.read()).state.rounds.length===1);
  let saved=(await source.read()).state;assert.deepEqual(saved.rounds[0].cases.map(c=>c.id),['C1']);assert.deepEqual(saved.rounds[0].selection.requestedCases,['C1']);await page.locator('#summary-view').click();assert((await page.locator('#test-conclusion').textContent()).includes('本轮冻结范围：C1'));await page.reload();await page.locator('#test-conclusion').getByText('本轮冻结范围：C1',{exact:false}).waitFor();
  await page.locator('#cases-view').click();await page.locator('#round-setup').evaluate(node=>node.open=true);await form.locator('[name=name]').fill('Full regression stale attempt');await form.locator('[name=fullRegression]').check();await page.locator('#preview-round').click();assert((await page.locator('#round-preview').textContent()).includes('冻结 49'));assert((await page.locator('#round-preview').textContent()).includes('完整回归将纳入整个方案'));
  await form.locator('[name=confirmed]').check();saved=(await source.read()).state;await source.write(saved.revision,m.editCase(saved,'p',{...saved.plans[0].cases[0],steps:'External change after preview'}));await form.locator('button[type=submit]').click();await page.locator('#message.error').waitFor();assert.equal((await source.read()).state.rounds.length,1);
  await page.locator('#reload').click();await page.waitForFunction(()=>document.documentElement.dataset.busy!=='true');assert(await form.locator('[name=confirmed]').isDisabled());await page.locator('#preview-round').click();await form.locator('[name=confirmed]').check();await form.locator('[name=name]').fill('Explicit full regression');await form.locator('button[type=submit]').click();await until(async()=>(await source.read()).state.rounds.length===2);assert.equal((await source.read()).state.rounds[1].cases.length,49);
  assert.deepEqual(errors,[]);await page.close();console.log(`PASS ${mode}: read-only preview/exclusions, mandatory confirmation/reset, branch scope, persisted scope, stale rejection and explicit full regression`);
 }
}finally{await browser.close();for(const app of apps)await app.close();await fs.rm(root,{recursive:true,force:true});}
