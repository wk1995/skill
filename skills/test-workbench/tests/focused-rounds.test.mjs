import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import * as m from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
import {FileSource,command} from '../scripts/workspace-sources.mjs';
import {FakeGitHub} from './fake-github.mjs';
const at='2026-11-10T00:00:00Z';
const item=id=>({id,title:id,types:['functional'],priority:'P1',preconditions:'',steps:'Execute',expected:'Observe'});
function fixture(){const cases=Array.from({length:49},(_,i)=>item(`C${i+1}`));cases[48].types=['smoke'];return m.importPlan(m.empty(),{id:'p',title:'Disposable scope fixture',revision:0,version:'fixture',source:'sha',build:'',pr:'',cases});}
const input=(s,ids=['C1','C2'])=>({id:'r',name:'Focused defect',createdAt:at,planId:'p',selection:{source:'issue',planRevision:s.plans[0].revision,cases:ids}});
function rejects(s,action,pattern){const before=structuredClone(s);assert.throws(()=>action(s),pattern);assert.deepEqual(s,before);}
function running(s){s=m.registerEnvironment(s,{id:'e',label:'Fixture',kind:'browser',configuration:'Disposable'});s=m.attachEnvironment(s,'r','e');for(const [id,action,from] of [['ready','prepare','draft'],['begin','begin','ready']])s=m.transitionRound(s,'r',{id,action,from,actor:'Fixture',at});return s;}

test('focused two-case scope excludes all unrelated smoke and previous failures; summary counts only selected pairs',()=>{
 let s=fixture(),previous=m.createRound(s,{...input(s,['C49']),id:'old'});previous=running({...previous,rounds:previous.rounds.map(r=>({...r,id:'r'}))});previous=m.startExecution(previous,'r',{id:'start',from:'untested',caseId:'C49',environmentId:'e',actor:'Fixture',at});previous=m.record(previous,'r',{id:'fail',caseId:'C49',environmentId:'e',environment:previous.environments[0],status:'failed',executedAt:at,recordedAt:at,tester:'Fixture',notes:'Actual fixture failure',evidence:'Fixture evidence'});previous.rounds[0].id='old';
 s=m.createRound(previous,input(previous));assert.deepEqual(s.rounds[1].cases.map(c=>c.id),['C1','C2']);assert.deepEqual(s.rounds[0],previous.rounds[0]);
 s=m.attachEnvironment(s,'r','e');const report=testConclusions(s).rounds[1];assert.equal(report.executions.length,2);assert.equal(report.counts.untested,2);assert.equal(report.counts.failed,0);assert.deepEqual(m.exportAI(s).projection.conclusions.rounds[1],report);
});

test('outcome branch chain never expands focused scope, changes conclusions or invents an executable target',()=>{
 let s=fixture();const p=structuredClone(s.plans[0]);p.revision++;for(let i=0;i<48;i++)p.cases[i].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:`C${i+2}`,reason:'Optional next test'}]));s=m.importPlan(s,p);
 const request=input(s,['C1']),before=structuredClone(s),preview=m.previewRoundSelection(s,request);assert.deepEqual(s,before);assert.deepEqual(preview.cases.map(c=>c.id),['C1']);s=running(m.createRound(s,request));
 s=m.record(s,'r',{id:'skip',caseId:'C1',environmentId:'e',environment:s.environments[0],status:'skipped',executedAt:null,recordedAt:at,tester:'Fixture',notes:'Outside required work',evidence:''});
 const advice=m.nextTest(s.rounds[0],'C1','e');assert.equal(advice.action,'out-of-scope');assert.equal(advice.excludedCaseId,'C2');assert.equal(advice.available,false);assert.equal(advice.target,null);
 const graph=m.projectFlow(s.rounds[0],{caseId:'C1',environmentId:'e'});assert.equal(graph.nodes.length,1);assert.equal(graph.edges.length,0);assert.equal(graph.nextTest.action,'out-of-scope');assert.equal(testConclusions(s).rounds[0].executions.length,1);assert.equal(m.exportAI(s).projection.rounds[0].executions[0].nextTest.action,'out-of-scope');
 const invalid=structuredClone(s);delete invalid.rounds[0].selection;rejects(m.empty(),x=>m.importArchive(x,invalid),/Next case not found|smoke/);
});

test('prerequisite closure is recursive, deduplicated, ordered and frozen without following unrelated routes',()=>{
 let s=fixture(),p=structuredClone(s.plans[0]);p.revision++;p.cases[0].dependsOn=['C2'];p.cases[1].dependsOn=['C3'];p.cases[2].next=Object.fromEntries(m.RESULTS.map(status=>[status,{action:'test',caseId:'C49',reason:'Optional branch'}]));s=m.importPlan(s,p);
 const request=input(s,['C1','C2']),preview=m.previewRoundSelection(s,request);assert.deepEqual(preview.cases.map(c=>c.id),['C3','C2','C1']);const saved=m.createRound(s,request);assert.deepEqual(saved.rounds[0].selection.requestedCases,['C1','C2']);assert.deepEqual(saved.rounds[0].selection.cases,['C3','C2','C1']);assert.deepEqual(saved.rounds[0].cases.map(c=>c.id),preview.cases.map(c=>c.id));
 assert.equal(m.createRound(saved,request),saved);const changed=m.editCase(saved,'p',{...saved.plans[0].cases[0],steps:'Later steps'});assert.deepEqual(changed.rounds,saved.rounds);assert.equal(m.importArchive(m.empty(),saved).rounds[0].cases[2].steps,'Execute');
});

test('direct preview/create reject missing, duplicate, unknown, stale or malformed selection before mutation',()=>{
 const s=fixture(),good=input(s);
 for(const selection of [undefined,null,{}, {...good.selection,cases:[]},{...good.selection,cases:['C1','C1']},{...good.selection,cases:['missing']},{...good.selection,cases:[3]},{...good.selection,planRevision:1},{...good.selection,source:'invented'},{...good.selection,source:'full-regression'}])for(const operation of [m.previewRoundSelection,m.createRound])rejects(s,x=>operation(x,{...good,selection}));
 for(const extra of [{changedIds:s.plans[0].cases.map(c=>c.id)},{includeUnfinished:true}])for(const operation of [m.previewRoundSelection,m.createRound])rejects(s,x=>operation(x,{...good,...extra}),/legacy/);
 const newer=m.editCase(s,'p',{...s.plans[0].cases[0],steps:'Changed after preview'});rejects(newer,x=>m.createRound(x,good),/stale/);
 const saved=m.createRound(s,good);rejects(saved,x=>m.createRound(x,{...good,name:'Conflicting retry'}),/already exists/);
 for(const edit of [r=>r.selection.cases.push('C49'),r=>r.selection.requestedCases=[],r=>r.selection.source='invented',r=>{r.cases.push({...s.plans[0].cases[48],selectionReasons:['selected']});r.selection.cases.push('C49');}]){const bad=structuredClone(saved);edit(bad.rounds[0]);rejects(m.empty(),x=>m.importArchive(x,bad));}
});

test('explicit full regression includes every case and old smoke archives remain readable without invented selection',()=>{
 const s=fixture(),request=input(s,s.plans[0].cases.map(c=>c.id));request.selection.source='full-regression';const all=m.createRound(s,request);assert.equal(all.rounds[0].cases.length,49);assert.equal(m.createRound(all,request),all);
 const legacy=structuredClone(all);delete legacy.rounds[0].selection;assert(m.validate(legacy));assert.equal(m.importArchive(legacy,structuredClone(legacy)),legacy);assert.equal(legacy.rounds[0].selection,undefined);
});

test('an exact creation retry uses the saved scope after a plan revision; stale requests cannot create new rounds',()=>{
 const s=fixture(),request=input(s),saved=m.createRound(s,request);
 const edited=m.editCase(saved,'p',{...saved.plans[0].cases[0],steps:'Edited after creation'});
 assert.equal(m.createRound(edited,request),edited);
 assert.equal(edited.rounds[0].cases[0].steps,'Execute');
 rejects(edited,x=>m.createRound(x,{...request,id:'new'}),/stale/);
 rejects(edited,x=>m.previewRoundSelection(x,request),/stale/);
 rejects(edited,x=>m.createRound(x,{...request,name:'Conflicting retry'}),/already exists/);
 rejects(edited,x=>m.createRound(x,{...request,selection:{...request.selection,cases:['C49']}}),/already exists/);
 rejects(edited,x=>m.createRound(x,{...request,changedIds:['C49']}),/legacy/);
});

test('focused archive and exact conclusion survive both primary sources; invalid scope writes preserve authority and repeats write nothing',async t=>{
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'focused-sources-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));await command('git',['init','-q','-b','main',root]);for(const [key,value] of [['user.name','Fixture'],['user.email','fixture@example.invalid'],['commit.gpgsign','false'],['core.hooksPath',os.devnull]])await command('git',['-C',root,'config',key,value]);await fs.writeFile(path.join(root,'README'),'Disposable');await command('git',['-C',root,'add','README']);await command('git',['-C',root,'commit','-qm','Fixture']);
 const api=new FakeGitHub(),sources=[api.source(),new FileSource({repoRoot:root})];let saved=running(m.createRound(fixture(),input(fixture())));saved.revision=1;
 for(const source of sources){await source.initialize();await source.write(0,saved);assert.deepEqual((await source.read()).state,saved);assert.equal(testConclusions((await source.read()).state).rounds[0].executions.length,2);const bad=structuredClone(saved);bad.revision++;bad.rounds[0].selection.cases.push('C49');await assert.rejects(source.write(1,bad));assert.deepEqual((await source.read()).state,saved);const count=api.writes();await source.write(1,structuredClone(saved));assert.equal(api.writes(),count);}
});
