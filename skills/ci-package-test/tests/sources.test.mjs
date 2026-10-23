import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import * as m from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
import {GitHubSource,FileSource,command,proposed} from '../scripts/workspace-sources.mjs';
import {createWorkbenchServer,options} from '../scripts/workbench-server.mjs';
import {FakeGitHub} from './fake-github.mjs';
const at='2026-10-23T09:00:00Z';
const plan=()=>({id:'p',version:'1.0.0',revision:0,title:'真实字符测试',source:'source-sha',build:'',pr:'',cases:[{id:'S',title:'Smoke',priority:'P0',types:['smoke'],preconditions:'Fixture',steps:'执行测试',expected:'符合预期'}]});
const env={id:'e',label:'fixture',kind:'browser',configuration:'isolated'};
function running(){let s=m.importPlan(m.empty(),plan());s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at});s=m.registerEnvironment(s,env);s=m.attachEnvironment(s,'r','e');s=m.transitionRound(s,'r',{id:'prepare',from:'draft',action:'prepare',actor:'Tester',at});return m.transitionRound(s,'r',{id:'begin',from:'ready',action:'begin',actor:'Tester',at});}
const nextPlan=s=>m.importPlan(s,plan());
function oneRevision(s,old){s.revision=old.revision+1;return s;}
async function fixture(t){const root=await fs.mkdtemp(path.join(os.tmpdir(),'testflow-files-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));await command('git',['init','-q','-b','main',root]);for(const [key,value] of [['user.name','Fixture'],['user.email','fixture@example.invalid'],['commit.gpgsign','false'],['core.hooksPath',os.devnull]])await command('git',['-C',root,'config',key,value]);await fs.writeFile(path.join(root,'README.md'),'Original\n');await command('git',['-C',root,'add','README.md']);await command('git',['-C',root,'commit','-qm','Fixture']);return root;}

test('shared source guard rejects stale updates, history rewrites/removal and invalid no-ops before writes',()=>{
 const current=running(),before=structuredClone(current);assert.equal(proposed(current,current.revision,structuredClone(current)),current);
 assert.throws(()=>proposed(current,current.revision-1,current),/变化/);
 for(const edit of [s=>s.rounds=[],s=>s.environments=[],s=>s.rounds[0].source='rewrite',s=>s.rounds[0].version='9',s=>s.rounds[0].workflow.events[0].actor='rewrite']){const bad=structuredClone(current);bad.revision++;edit(bad);assert.throws(()=>proposed(current,current.revision,bad));assert.deepEqual(current,before);}
});

test('GitHub default source initializes explicitly and persists case/round/annotation documents, chunks and conclusions',async()=>{
 const api=new FakeGitHub(),source=api.source();await source.preflight();const first=await source.read();assert.equal(first.info.initialized,false);assert.equal(api.writes(),0);
 await source.initialize();const writes=api.writes();await source.initialize();assert.equal(api.writes(),writes);
 let candidate=running();candidate.plans[0].cases[0].steps='长文本😀'.repeat(5000);candidate=oneRevision(candidate,m.empty());
 const saved=await source.write(0,candidate);assert.deepEqual(saved.state,candidate);assert.equal(saved.info.mode,'github-issues');assert(api.items.size>=3);assert(api.comments.size>4);
 const newSession=api.source();await newSession.preflight();assert.deepEqual((await newSession.read()).state,candidate);
 const comments=api.comments.size;await source.write(candidate.revision,structuredClone(candidate));assert.equal(api.comments.size,comments);
 const note=m.addAnnotation(candidate,{id:'n',planId:'p',roundId:'r',caseId:'S',target:{field:'case',quote:''},event:{id:'c',kind:'comment',author:'Tester',body:'Review',createdAt:at}});assert.deepEqual((await source.write(candidate.revision,note)).state.annotations,note.annotations);
 const chunks=[...api.comments.values()].map(c=>c.body);assert(chunks.some(body=>body.includes('conclusions')));assert(chunks.every(body=>body.length<65000));
});

test('GitHub partial writes never publish; uncertain final publication is inspected and verified, not retried',async()=>{
 const api=new FakeGitHub(),source=api.source();await source.initialize();const before=await source.read();const candidate=nextPlan(before.state);
 api.fail=(method,route)=>method==='POST'&&route.endsWith('/comments')?'before':null;await assert.rejects(source.write(0,candidate),/injected/);api.fail=null;assert.deepEqual((await source.read()).state,before.state);
 api.fail=(method)=>method==='PATCH'?'after':null;assert.deepEqual((await source.write(0,candidate)).state,candidate);assert.equal(api.calls.filter(c=>c.method==='PATCH').length,1);
 api.fail=null;const count=api.writes();await assert.rejects(source.write(0,candidate),/变化/);assert.equal(api.writes(),count);
 api.actor='another';await assert.rejects(source.write(candidate.revision,candidate),/账号/);assert.equal(api.writes(),count);
});

test('GitHub reader rejects corrupted referenced evidence, wrong Issue binding and ambiguous workspace identity',async()=>{
 const api=new FakeGitHub(),source=api.source();await source.initialize();await source.write(0,nextPlan(m.empty()));const first=[...api.comments.values()][0],original=structuredClone(first);
 first.issue_url='https://api.github.com/repos/other/repo/issues/1';await assert.rejects(source.read(),/another Issue/);Object.assign(first,original);
 first.body=first.body.replace('Smoke','Changed');await assert.rejects(source.read(),/digest/);Object.assign(first,original);
 const index=api.items.get(source.index);api.items.set(999,{...structuredClone(index),number:999});await assert.rejects(api.source().read(),/多个/);
});

test('file source saves separate files/conclusions without committing, explicitly commits only test data, and is idempotent',async t=>{
 const root=await fixture(t),source=new FileSource({repoRoot:root});const initialHead=await source.git(['rev-parse','HEAD']);assert.equal((await source.read()).info.initialized,false);
 await source.initialize();const state=oneRevision(running(),m.empty());await source.write(0,state);assert.equal(await source.git(['rev-parse','HEAD']),initialHead);
 const pointer=JSON.parse(await fs.readFile(path.join(root,'testing/testflow/workspace.json'))),dir=path.join(root,'testing/testflow/snapshots',pointer.generation);const records=JSON.parse(await fs.readFile(path.join(dir,'records.json'))),report=JSON.parse(await fs.readFile(path.join(dir,'conclusions.json')));
 assert.equal(records[0].id,'r');assert.deepEqual(report,testConclusions(state));assert.equal(report.rounds[0].verdict,'incomplete');
 await fs.writeFile(path.join(root,'unrelated.txt'),'Do not commit me');await source.git(['add','unrelated.txt']);await fs.writeFile(path.join(root,'testing/testflow/notes.txt'),'Unselected file');
 const saved=await source.commit(state.revision);assert.equal(saved.info.persistence,'committed');const files=(await source.git(['show','--pretty=format:','--name-only','HEAD'])).split('\n');assert(files.includes('testing/testflow/workspace.json'));assert(files.some(f=>f.endsWith('/conclusions.json')));assert(!files.includes('unrelated.txt'));assert(!files.includes('testing/testflow/notes.txt'));
 assert.equal(await source.git(['diff','--cached','--name-only']),'unrelated.txt');const head=saved.info.head;assert.equal((await source.commit(state.revision)).info.head,head);
 assert.deepEqual((await new FileSource({repoRoot:root}).read()).state,state);
});

test('file failure preserves previous pointer, retries successfully and rejects invalid updates before new files',async t=>{
 const root=await fixture(t);let failing=false;const source=new FileSource({repoRoot:root,beforePublish:async()=>{if(failing)throw new Error('publication fault');}});await source.initialize();const before=await source.read(),pointer=await fs.readFile(path.join(root,'testing/testflow/workspace.json'));
 failing=true;await assert.rejects(source.write(0,nextPlan(before.state)),/fault/);assert.deepEqual((await source.read()).state,before.state);assert.deepEqual(await fs.readFile(path.join(root,'testing/testflow/workspace.json')),pointer);
 failing=false;const saved=await source.write(0,nextPlan(before.state));assert.equal(saved.state.plans.length,1);const names=await fs.readdir(path.join(root,'testing/testflow/snapshots'));await source.write(saved.state.revision,structuredClone(saved.state));assert.deepEqual(await fs.readdir(path.join(root,'testing/testflow/snapshots')),names);
 const bad=structuredClone(saved.state);bad.plans=[];bad.revision++;await assert.rejects(source.write(saved.state.revision,bad));assert.deepEqual(await fs.readdir(path.join(root,'testing/testflow/snapshots')),names);assert.equal((await source.commit(saved.state.revision)).info.persistence,'committed');
});

test('file path containment, root aliases, foreign content and nested symlinks reject before mutation',async t=>{
 const root=await fixture(t),outside=await fs.mkdtemp(path.join(os.tmpdir(),'testflow-outside-'));t.after(()=>fs.rm(outside,{recursive:true,force:true}));
 for(const dataDir of ['.','..','../outside','.git','a/.GiT/b','/tmp/outside'])assert.throws(()=>new FileSource({repoRoot:root,dataDir}));
 await fs.mkdir(path.join(root,'foreign'));await fs.writeFile(path.join(root,'foreign','keep'),'keep');await assert.rejects(new FileSource({repoRoot:root,dataDir:'foreign'}).initialize(),/已有/);assert.equal(await fs.readFile(path.join(root,'foreign/keep'),'utf8'),'keep');
 await fs.symlink(outside,path.join(root,'linked'));await assert.rejects(new FileSource({repoRoot:root,dataDir:'linked/nested'}).initialize(),/符号/);assert.deepEqual(await fs.readdir(outside),[]);
 const source=new FileSource({repoRoot:root});await source.initialize();const folder=path.join(root,'testing/testflow/snapshots'),backup=folder+'-backup';await fs.rename(folder,backup);await fs.symlink(backup,folder);await assert.rejects(source.read(),/符号/);await assert.rejects(source.write(0,nextPlan(m.empty())),/符号/);await assert.rejects(source.commit(0),/符号/);
});

test('file commit rejects detached, stale and ignored data; preserves data and unrelated staging on failure',async t=>{
 const root=await fixture(t),source=new FileSource({repoRoot:root});await source.initialize();await assert.rejects(source.commit(999),/刷新/);
 await source.git(['checkout','--detach','-q']);await assert.rejects(source.commit(0),/Detached/);await source.git(['switch','main']);
 await fs.writeFile(path.join(root,'.gitignore'),'testing/\n');await assert.rejects(source.commit(0),/ignored/);assert.equal((await source.read()).state.revision,0);assert.equal(await source.git(['diff','--cached','--name-only']),'');
});

test('derived conclusions retain failures and incomplete coverage and require completed all-pass for passing',()=>{
 let state=running();const result=(s,id,status)=>m.record(m.startExecution(s,'r',{id:'start-'+id,from:m.executionState(s.rounds[0],'S','e'),caseId:'S',environmentId:'e',actor:'Tester',at}),'r',{id,caseId:'S',environmentId:'e',environment:env,status,executedAt:at,recordedAt:at,tester:'Tester',notes:'Observed',evidence:'fixture'});
 state=result(state,'bad','failed');assert.equal(testConclusions(state).rounds[0].verdict,'failed');state=result(state,'skip','skipped');assert.equal(testConclusions(state).rounds[0].verdict,'failed');state=result(state,'fixed','passed');assert.equal(testConclusions(state).rounds[0].verdict,'incomplete');state=m.transitionRound(state,'r',{id:'done',from:'running',action:'complete',actor:'Tester',at});assert.equal(testConclusions(state).rounds[0].verdict,'passed');assert.equal(m.exportAI(state).projection.conclusions.rounds[0].verdict,'passed');
});

test('HTTP bridge enforces host/origin/session and complete validation before source writes, serves actual modules',async t=>{
 const root=await fixture(t),source=new FileSource({repoRoot:root}),app=await createWorkbenchServer({source});t.after(()=>app.close());const config=await (await fetch(app.url+'/api/config')).json();assert.equal(config.mode,'repository-files');
 for(const headers of [{Origin:'https://other.invalid'},{Host:'other.invalid'},{'Sec-Fetch-Site':'cross-site'}]){const status=await new Promise((resolve,reject)=>http.get(app.url+'/api/config',{headers},res=>{res.resume();resolve(res.statusCode);}).on('error',reject));assert.equal(status,400,JSON.stringify(headers));}
 assert.equal((await fetch(app.url+'/api/initialize',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,400);assert.equal((await source.read()).info.initialized,false);
 const headers={'Content-Type':'application/json','X-Testflow-Session':config.session};let res=await fetch(app.url+'/api/initialize',{method:'POST',headers,body:'{}'});assert.equal(res.status,200);
 res=await fetch(app.url+'/api/workspace',{method:'PUT',headers,body:JSON.stringify({expectedRevision:0,state:nextPlan(m.empty())})});assert.equal(res.status,200);assert.equal((await res.json()).state.plans[0].title,'真实字符测试');
 res=await fetch(app.url+'/api/workspace',{method:'PUT',headers,body:JSON.stringify({expectedRevision:0,state:m.empty()})});assert.equal(res.status,400);assert.equal((await source.read()).state.plans.length,1);
 assert.equal((await fetch(app.url+'/app.mjs')).status,200);assert.equal((await fetch(app.url+'/scripts/workspace-sources.mjs')).status,400);assert.equal((await fetch(app.url+'/api/other')).status,404);
 assert.equal(options([]).mode,'github-issues');assert.throws(()=>options(['--mode','anything']));
});

test('missing gh/Git fail before initialization and request bodies go through stdin, not command interpolation',async t=>{
 const root=await fixture(t),noPath=path.join(root,'no-tools');await fs.mkdir(noPath);const run=(exe,args,opts)=>command(exe,args,{...opts,env:{...process.env,PATH:noPath}});
 await assert.rejects(new GitHubSource({repo:'owner/repo',run}).initialize(),/gh unavailable/);await assert.rejects(new FileSource({repoRoot:root,run}).initialize(),/git unavailable/);await assert.rejects(fs.stat(path.join(root,'testing')),/ENOENT/);
 const api=new FakeGitHub(),source=new GitHubSource({repo:'owner/repo',run:async(exe,args,opts)=>{assert.equal(exe,'gh');assert.equal(args[0],'api');assert.equal(args[2],'github.com');return JSON.stringify(await api.api(args[4],args[5],opts.input?JSON.parse(opts.input):undefined));}});
 await source.initialize();const p=plan();p.cases[0].title='Literal `command` $(echo no) text';const candidate=m.importPlan(m.empty(),p);assert.deepEqual((await source.write(0,candidate)).state,candidate);
});

test('file commit validates older generations and leaves unrelated staging intact after hook failure/retry',async t=>{
 const root=await fixture(t),source=new FileSource({repoRoot:root});await source.initialize();const old=JSON.parse(await fs.readFile(path.join(root,'testing/testflow/workspace.json')));await source.write(0,nextPlan(m.empty()));const conclusions=path.join(root,'testing/testflow/snapshots',old.generation,'conclusions.json'),bytes=await fs.readFile(conclusions);
 await fs.writeFile(conclusions,'{}');await assert.rejects(source.commit(1),/conclusion/);assert.equal(await source.git(['diff','--cached','--name-only']),'');await fs.writeFile(conclusions,bytes);
 const hooks=path.join(root,'hooks');await fs.mkdir(hooks);await fs.writeFile(path.join(hooks,'pre-commit'),'#!/bin/sh\nexit 1\n',{mode:0o755});await source.git(['config','core.hooksPath',hooks]);await fs.writeFile(path.join(root,'unrelated'),'staged');await source.git(['add','unrelated']);const head=await source.git(['rev-parse','HEAD']);await assert.rejects(source.commit(1));assert.equal(await source.git(['rev-parse','HEAD']),head);assert((await source.git(['diff','--cached','--name-only'])).includes('unrelated'));assert.equal((await source.read()).state.plans.length,1);
 await source.git(['config','core.hooksPath',os.devnull]);assert.equal((await source.commit(1)).info.persistence,'committed');assert.equal(await source.git(['diff','--cached','--name-only']),'unrelated');
});

test('literal Git pathspecs and case/symlink aliases cannot redirect data commits',async t=>{
 const root=await fixture(t),source=new FileSource({repoRoot:root,dataDir:':(top)literal'});await source.initialize();assert.equal((await source.commit(0)).info.persistence,'committed');assert((await source.git(['show','--pretty=format:','--name-only','HEAD'])).includes(':(top)literal/workspace.json'));
 const normal=new FileSource({repoRoot:root});await normal.initialize();
 try{await fs.stat(path.join(root,'Testing/testflow'));await assert.rejects(new FileSource({repoRoot:root,dataDir:'Testing/testflow'}).initialize(),/exact filesystem path spelling/);}catch(error){if(error.code!=='ENOENT')throw error;}
 const pointer=JSON.parse(await fs.readFile(path.join(root,'testing/testflow/workspace.json')));
 for(const relative of ['owner.json','workspace.json',...['definitions.json','records.json','annotations.json','conclusions.json'].map(f=>path.join('snapshots',pointer.generation,f))]){
  const file=path.join(root,'testing/testflow',relative),saved=await fs.readFile(file);await fs.rename(file,file+'.original');await fs.symlink(file+'.original',file);await assert.rejects(normal.read(),/符号/);await assert.rejects(normal.initialize(),/符号/);await assert.rejects(normal.commit(0),/符号/);await fs.unlink(file);await fs.rename(file+'.original',file);assert.deepEqual(await fs.readFile(file),saved);
 }
});

test('browser remote adapter pins repository/workspace identity and preserves data on an expired service session',async()=>{
 const {readRemote,updateRemote}=await import('../assets/workbench/remote-store.mjs');const original=globalThis.fetch;let target={mode:'github-issues',repository:'github.com/owner/repo',workspace:'default'};
 globalThis.fetch=async(_url,opts)=>opts?.method==='PUT'?Response.json({error:'Missing session token'},{status:400}):Response.json({state:m.empty(),info:target});
 try{const store={remote:true,session:'old',info:{mode:'github-issues'}};await readRemote(store);const originalInfo=store.info;target={...target,repository:'github.com/other/repo'};await assert.rejects(readRemote(store),/数据源发生变化/);assert.equal(store.info,originalInfo);target=originalInfo;await assert.rejects(updateRemote(store,0,nextPlan),/连接已过期/);}finally{globalThis.fetch=original;}
});

test('command streaming preserves split UTF-8 and Git location environment cannot redirect the selected repository',async t=>{
 const text='真实字符😀';assert.equal(await command(process.execPath,['-e',`const b=Buffer.from(${JSON.stringify(text)});let i=0;function emit(){if(i<b.length){process.stdout.write(b.subarray(i,++i));setTimeout(emit,1);}}emit();`]),text);
 const root=await fixture(t),other=await fixture(t),before=await command('git',['-C',other,'rev-parse','HEAD']);
 const run=(exe,args,opts)=>command(exe,args,{...opts,env:{...process.env,GIT_DIR:path.join(other,'.git'),GIT_WORK_TREE:root,GIT_INDEX_FILE:path.join(other,'.git/index')}});
 const source=new FileSource({repoRoot:root,run});await source.initialize();await source.commit(0);assert.equal(await command('git',['-C',other,'rev-parse','HEAD']),before);assert.equal((await source.read()).info.dirty,false);
});

test('server CLI remains executable through a linked Skill and rejects inherited option names',async t=>{
 const root=await fixture(t),link=path.join(root,'linked-server.mjs');await fs.symlink(new URL('../scripts/workbench-server.mjs',import.meta.url),link);assert.match(await command(process.execPath,[link,'--help']),/--repo OWNER\/REPO/);assert.throws(()=>options(['toString','anything','--repo','owner/repo']),/Unknown/);
});

test('Git diagnostics do not refresh or lock the index while testing data is being read',async t=>{
 const root=await fixture(t),file=path.join(root,'README.md'),index=path.join(root,'.git/index'),before=await fs.readFile(index);const later=new Date(Date.now()+10000);await fs.utimes(file,later,later);await command('git',['-C',root,'status','--porcelain'],{env:{...process.env,GIT_OPTIONAL_LOCKS:'1'}});assert.deepEqual(await fs.readFile(index),before);
});

test('unborn repositories reject initialization before creating any test data',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'testflow-unborn-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));await command('git',['init','-q',root]);await assert.rejects(new FileSource({repoRoot:root}).initialize(),/revision|HEAD/);assert.deepEqual(await fs.readdir(root),['.git']);
});
