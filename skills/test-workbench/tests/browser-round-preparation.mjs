import {createRequire} from 'node:module';
import {mkdtemp, rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createWorkbenchServer} from '../scripts/workbench-server.mjs';
import {FileSource, command} from '../scripts/workspace-sources.mjs';
import {FakeGitHub} from './fake-github.mjs';
import {multiChangeArchive} from './round-preparation-fixture.mjs';

const {chromium}=createRequire(import.meta.url)(process.env.TESTFLOW_PLAYWRIGHT_MODULE??'playwright');
const browser=await chromium.launch({headless:true,...(process.env.TESTFLOW_CHROME?{executablePath:process.env.TESTFLOW_CHROME}:{})});
const root=await mkdtemp(path.join(os.tmpdir(),'workbench-round-nav-'));
try{
  await command('git',['init','-q','-b','main',root]);
  await command('git',['-C',root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath='+os.devnull,'commit','--allow-empty','-qm','Fixture']);
  for(const source of [new FileSource({repoRoot:root}),new FakeGitHub().source()]){
    await source.initialize();
    const fixture=multiChangeArchive();fixture.revision=1;
    await source.write(0,fixture);
    const app=await createWorkbenchServer({source}),page=await browser.newPage();
    try{
      const oldLink='#plan=p&round=release&case=A&view=cases';
      await page.goto(app.url+oldLink);
      await page.locator('#detail [data-case-id="A"]').first().waitFor();
      assert.equal(await page.locator('#round').inputValue(),'release');
      assert.match(await page.locator('#round option:checked').textContent(),/完整回归/);
      await page.locator('#case-library').click();
      assert.equal(await page.locator('#round').inputValue(),'');
      assert.equal(await page.locator('form.editor').count(),1);
      await page.locator('#round-setup summary').click();
      const form=page.locator('#round-form'),preview=page.locator('#round-preview');
      await form.locator('[name=unfinished]').check();
      await page.locator('#preview-round').click();
      assert.match(await preview.textContent(),/冻结 2.*release-sha/s);
      await form.locator('[name=confirmed]').check();
      await form.locator('[name=unfinishedRound]').selectOption('fix');
      assert(await form.locator('[name=confirmed]').isDisabled());
      await page.locator('#preview-round').click();
      assert.match(await preview.textContent(),/冻结 1.*fix-sha/s);
      assert.deepEqual((await source.read()).state,fixture);
      await source.write(1,{...fixture,revision:2,plans:[{...fixture.plans[0],revision:3,pr:'other'}]});
      await page.locator('#reload').click();
      await page.waitForFunction(()=>document.documentElement.dataset.busy==='false');
      assert(await form.locator('[name=confirmed]').isDisabled());
      await form.locator('[name=unfinishedRound]').selectOption('');
      await page.locator('#preview-round').click();
      assert.match(await page.locator('#message.error').textContent(),/明确选择/);
      await page.goto(app.url+'#plan=p&round=missing&case=A&view=cases');
      await page.getByText(/链接中的轮次不存在：missing/).waitFor();
      assert.equal((await source.read()).state.revision,2);
      console.log('PASS '+(await source.read()).info.mode+': original deep link, case library, compatible and explicit previews, stale confirmation, missing round');
    }finally{await page.close();await app.close();}
  }
}finally{await browser.close();await rm(root,{recursive:true,force:true});}
