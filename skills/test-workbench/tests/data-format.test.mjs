import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {validateTestData,options} from '../scripts/validate-test-data.mjs';
import * as m from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
import {FileSource,command} from '../scripts/workspace-sources.mjs';
import {FakeGitHub} from './fake-github.mjs';
const run=promisify(execFile),script=fileURLToPath(new URL('../scripts/validate-test-data.mjs',import.meta.url));
const example=name=>fs.readFile(new URL(`../assets/examples/${name}.json`,import.meta.url),'utf8').then(JSON.parse);
async function temp(t){const dir=await fs.mkdtemp(path.join(os.tmpdir(),'test-data-format-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));return dir;}

test('canonical format fixtures replay completely and AI field metadata agrees with real data',async()=>{
 const archive=await example('archive'),plan=await example('plan'),conclusions=await example('conclusions'),before=structuredClone(archive);
 assert.equal(validateTestData(plan,{kind:'plan'}).valid,true);assert.equal(validateTestData(archive,{conclusions}).conclusions,'verified');assert.deepEqual(testConclusions(archive),conclusions);assert.deepEqual(archive,before);
 const round=archive.rounds[0],report=conclusions.rounds[0];assert.equal(m.inspectWorkflow(round).state,'completed');assert.equal(report.verdict,'failed');assert.equal(report.counts.passed,1);assert.equal(report.counts.failed,1);assert.deepEqual(m.nextTest(round,'LOGIN01','EXAMPLE-ENV').target.id,'PROFILE01');
 const pairs=[[m.CONTRACT.data.archive,archive],[m.CONTRACT.data.plan,plan],[m.CONTRACT.data.case,plan.cases[0]],[m.CONTRACT.data.round,round],[m.CONTRACT.data.environment,archive.environments[0]],[m.CONTRACT.data.observation,round.observations[0]],[m.CONTRACT.data.issueLinks,round.issueLinks[0]],[m.CONTRACT.data.workflow,round.workflow],[m.CONTRACT.data.conclusions,conclusions]];
 for(const [contract,data] of pairs)for(const key of contract.required)assert(Object.hasOwn(data,key),key);
 for(const key of m.CONTRACT.data.conclusions.roundRequired)assert(Object.hasOwn(report,key),key);
 for(const key of m.CONTRACT.data.conclusions.executionRequired)assert(Object.hasOwn(report.executions[0],key),key);
 assert.deepEqual(m.exportAI(archive).contract.data,m.CONTRACT.data);
});

test('shared validator rejects missing fields, invalid cross-references/events and fabricated or stale summaries without changing inputs',async()=>{
 const archive=await example('archive'),conclusions=await example('conclusions');
 for(const edit of [s=>delete s.rounds[0].observations[0].tester,s=>s.rounds[0].observations[0].caseId='missing',s=>s.rounds[0].version='wrong',s=>s.rounds[0].workflow.events.splice(2,1),s=>s.plans[0].cases[1].dependsOn=['missing'],s=>s.rounds[0].issueLinks[0].url='javascript:bad']){
  const bad=structuredClone(archive);edit(bad);const before=structuredClone(bad);assert.throws(()=>validateTestData(bad));assert.deepEqual(bad,before);
 }
 for(const edit of [s=>s.archiveRevision++,s=>s.rounds[0].verdict='passed',s=>s.rounds[0].counts.failed=0,s=>s.rounds[0].executions[1].issues=[],s=>s.rounds[0].executions.reverse(),s=>delete s.rounds[0].meaning,s=>s.extra='invented']){const bad=structuredClone(conclusions);edit(bad);assert.throws(()=>validateTestData(archive,{conclusions:bad}),/match/);}
 const reordered=Object.fromEntries(Object.entries(conclusions).reverse());assert.equal(validateTestData(archive,{conclusions:reordered}).valid,true);
 for(const value of [null,[],{},'passed'])assert.throws(()=>validateTestData(archive,{conclusions:value}));
 assert.throws(()=>validateTestData(archive,{kind:'unsupported'}));assert.throws(()=>validateTestData(archive.plans[0],{kind:'plan',conclusions}));
});

test('read-only CLI validates explicit files, fails closed and runs without Git/gh or network helpers',async t=>{
 const dir=await temp(t),archiveFile=path.join(dir,'archive.json'),summaryFile=path.join(dir,'conclusions.json'),planFile=path.join(dir,'plan.json');
 for(const [name,file] of [['archive',archiveFile],['conclusions',summaryFile],['plan',planFile]])await fs.writeFile(file,JSON.stringify(await example(name)));
 const before=Object.fromEntries(await Promise.all((await fs.readdir(dir)).map(async name=>[name,await fs.readFile(path.join(dir,name),'utf8')])));
 const env={...process.env,PATH:path.join(dir,'missing-tools')};
 for(const args of [['--plan',planFile],['--archive',archiveFile],['--archive',archiveFile,'--conclusions',summaryFile]])assert.equal(JSON.parse((await run(process.execPath,[script,...args],{env})).stdout).valid,true);
 const linked=path.join(dir,'linked-validator.mjs');await fs.symlink(script,linked);assert.match((await run(process.execPath,[linked,'--help'],{env})).stdout,/Read-only/);
 for(const args of [[],['constructor','x','--archive',archiveFile],['--archive',archiveFile,'--plan',planFile],['--archive',archiveFile,'--archive',archiveFile],['--plan',planFile,'--conclusions',summaryFile],['--archive'],['--help','--archive',archiveFile],['--archive',path.join(dir,'missing.json')]])await assert.rejects(run(process.execPath,[script,...args],{env}));
 const malformed=path.join(dir,'malformed.json');await fs.writeFile(malformed,'{invalid');await assert.rejects(run(process.execPath,[script,'--archive',malformed],{env}),error=>error.code===1&&error.stderr.includes('Cannot read JSON'));
 for(const [name,bytes] of Object.entries(before))assert.equal(await fs.readFile(path.join(dir,name),'utf8'),bytes);
 assert.deepEqual((await fs.readdir(dir)).sort(),[...Object.keys(before),'linked-validator.mjs','malformed.json'].sort());
 for(const args of [['--unknown','x'],['toString','x','--archive','a']])assert.throws(()=>options(args));
});

test('same canonical records and conclusion decode from both primary sources without format conversion',async t=>{
 const root=await temp(t);await command('git',['init','-q','-b','main',root]);for(const [key,value] of [['user.name','Fixture'],['user.email','fixture@example.invalid'],['commit.gpgsign','false'],['core.hooksPath',os.devnull]])await command('git',['-C',root,'config',key,value]);await fs.writeFile(path.join(root,'README.md'),'Disposable format fixture');await command('git',['-C',root,'add','README.md']);await command('git',['-C',root,'commit','-qm','Fixture']);
 const archive=await example('archive');archive.revision=1;const conclusions=testConclusions(archive),files=new FileSource({repoRoot:root}),api=new FakeGitHub(),github=api.source();
 for(const source of [files,github]){await source.initialize();assert.deepEqual((await source.write(0,archive)).state,archive);const decoded=(await source.read()).state;assert.equal(validateTestData(decoded,{conclusions}).conclusions,'verified');assert.deepEqual(testConclusions(decoded),conclusions);
  const bad=structuredClone(archive);bad.revision++;bad.rounds[0].observations[0].caseId='missing';await assert.rejects(source.write(1,bad));assert.deepEqual((await source.read()).state,archive);
 }
 const pointer=JSON.parse(await fs.readFile(path.join(root,'testing/testflow/workspace.json'),'utf8')),snapshot=path.join(root,'testing/testflow/snapshots',pointer.generation);assert.deepEqual(JSON.parse(await fs.readFile(path.join(snapshot,'records.json'),'utf8')),archive.rounds);assert.deepEqual(JSON.parse(await fs.readFile(path.join(snapshot,'conclusions.json'),'utf8')),conclusions);
});
