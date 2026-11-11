import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import {mkdtemp, rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createWorkbenchServer} from '../scripts/workbench-server.mjs';
import {FileSource, command} from '../scripts/workspace-sources.mjs';
import {verifyDeliveredArchive} from '../scripts/verify-delivered-archive.mjs';
import {FakeGitHub} from './fake-github.mjs';
import {archiveFixture, initFixtureRepo} from './delivered-archive-fixture.mjs';

const {chromium}=createRequire(import.meta.url)(process.env.TESTFLOW_PLAYWRIGHT_MODULE??'playwright');
const browser=await chromium.launch({headless:true,...(process.env.TESTFLOW_CHROME?{executablePath:process.env.TESTFLOW_CHROME}:{})});
const root=await mkdtemp(path.join(os.tmpdir(),'browser-delivered-'));
const {definitions,state,expected}=archiveFixture();
const original='#plan=p&round=old&view=records&case=A&environment=e&observation=original-observation';
async function visit(source,fragment,verify){
  const app=await createWorkbenchServer({source}),page=await browser.newPage();
  try{await page.goto(app.url+fragment);await verify(page);}
  finally{await page.close();await app.close();}
}
try{
  const repo=path.join(root,'repo'),clone=path.join(root,'clone');
  await initFixtureRepo(repo);
  const api=new FakeGitHub();
  for(const [mode,source] of [['repository-files',new FileSource({repoRoot:repo})],['github-issues',api.source()]]){
    await visit(source,original,async page=>{
      await page.getByText(mode==='repository-files'?/找不到仓库文件工作台入口，无法读取轮次 old/:/找不到 GitHub 工作台索引，无法读取轮次 old/).waitFor();
      assert.equal(await page.locator('#record-history').count(),0);
      assert.equal(new URL(page.url()).hash,original);
    });
    await source.initialize();await source.write(0,definitions);await source.write(1,state);
    let recovered=api.source();
    if(mode==='repository-files'){
      await source.commit(2);
      await command('git',['clone','--quiet','--no-local',repo,clone]);
      recovered=new FileSource({repoRoot:clone});
    }
    const verified=await verifyDeliveredArchive(recovered,expected);
    assert.equal(verified.rounds[0].link,original);
    await visit(recovered,original,async page=>{
      const record=page.locator('#observation-original-observation');
      await record.getByText('Original failure').waitFor();
      await record.getByRole('link',{name:/issues\/17/}).waitFor();
      assert.equal(await page.locator('#round').inputValue(),'old');
      assert.match(await page.locator('#identity').textContent(),/old-sha/);
      await page.locator('#summary-view').click();
      await page.locator('#test-conclusion').getByText(/本轮测试结论：未通过/).waitFor();
    });
    assert.deepEqual((await recovered.read()).state,state);
    console.log('PASS '+mode+': fresh browser reports missing archive and opens original observation and verdict after recovery');
  }
}finally{await browser.close();await rm(root,{recursive:true,force:true});}
