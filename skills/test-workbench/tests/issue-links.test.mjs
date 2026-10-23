import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
import {proposed} from '../scripts/workspace-sources.mjs';
const at='2026-10-23T09:00:00Z',url='https://github.com/fixture/project/issues/12';
const link=(extra={})=>({id:'link',observationId:'o',url,actor:'Tester',createdAt:at,...extra});
function fixture(){
 let s=m.importPlan(m.empty(),{id:'p',version:'1.0.0',revision:0,title:'Fixture',source:'sha',build:'',pr:'',cases:[{id:'S',title:'Smoke',priority:'P0',types:['smoke'],preconditions:'Fixture',steps:'Execute',expected:'Observe'}]});
 s=m.createRound(s,{id:'r',planId:'p',name:'Round',createdAt:at});s=m.registerEnvironment(s,{id:'e',label:'Fixture',kind:'browser',configuration:'Disposable'});s=m.attachEnvironment(s,'r','e');
 for(const [id,action,from] of [['prepare','prepare','draft'],['begin','begin','ready']])s=m.transitionRound(s,'r',{id,action,from,actor:'Tester',at});
 return m.startExecution(s,'r',{id:'start',from:'untested',caseId:'S',environmentId:'e',actor:'Tester',at});
}
const observation=s=>({id:'o',caseId:'S',environmentId:'e',environment:s.environments[0],status:'failed',executedAt:at,recordedAt:at,tester:'Tester',notes:'Observed failure; screenshots and logs in Issue',evidence:''});
function rejectUnchanged(s,fn){const before=structuredClone(s);assert.throws(()=>fn(s));assert.deepEqual(s,before);}

test('Issue URL parser canonicalizes links and rejects non-Issue and unsafe targets',()=>{
 assert.deepEqual(m.parseIssueURLs(` ${url}/#issuecomment-1\n${url}\nhttps://git.example.test/org/repo/issues/3`),[url,'https://git.example.test/org/repo/issues/3']);
 for(const value of ['#12','javascript:alert(1)','http://github.com/a/b/issues/1','https://u:p@github.com/a/b/issues/1','https://github.com/a/b/pull/1','https://github.com/a/b/issues/0','https://github.com/a/b/issues/1?token=x','https://github.com/a/b/issues/1/extra','https://github.com/a%2Fb/c/issues/1'])assert.throws(()=>m.issueURL(value));
});
test('Issue-only failure saves atomically and projects references without changing verdict',()=>{
 const s=fixture(),o=observation(s);rejectUnchanged(s,s=>m.record(s,'r',o));
 const next=m.recordBatch(s,'r',[o],[link()]);assert.equal(next.revision,s.revision+1);assert.deepEqual(next.rounds[0].observations,[o]);assert.deepEqual(m.recordIssues(next.rounds[0],'o'),[url]);
 assert.equal(m.inspectWorkflow(next.rounds[0]).executions[0].state,'failed');const report=testConclusions(next).rounds[0];assert.equal(report.verdict,'failed');assert.deepEqual(report.executions[0].issues,[url]);assert.deepEqual(m.exportAI(next).projection.conclusions.rounds[0],report);
 let retest=m.startExecution(next,'r',{id:'retry',from:'failed',caseId:'S',environmentId:'e',actor:'Tester',at});retest=m.record(retest,'r',{...o,id:'skip',status:'skipped'});assert.equal(testConclusions(retest).rounds[0].verdict,'failed');assert.deepEqual(testConclusions(retest).rounds[0].executions[0].issues,[url]);
 for(const bad of [link({url:'javascript:x'}),link({observationId:'missing'}),link({actor:''}),link({createdAt:'2026-02-30T00:00:00Z'})]){rejectUnchanged(s,s=>m.recordBatch(s,'r',[o],[link(),bad]));rejectUnchanged(s,s=>m.recordBatch(s,'r',[o],[bad]));}
 const noNotes={...o,notes:''};rejectUnchanged(s,s=>m.recordBatch(s,'r',[noNotes],[link()]));
});
test('existing completed records accept append-only associations, merge idempotently and reject rewrites/removal',()=>{
 let s=fixture();s=m.record(s,'r',{...observation(s),evidence:'Existing evidence'});s=m.transitionRound(s,'r',{id:'complete',action:'complete',from:'running',actor:'Tester',at});
 const emptyLinks=structuredClone(s);emptyLinks.rounds[0].issueLinks=[];emptyLinks.revision++;assert.deepEqual(proposed(s,s.revision,emptyLinks),emptyLinks);
 const before=structuredClone(s),next=m.linkRecordIssues(s,'r',[link()]);assert.deepEqual(next.rounds[0].observations,before.rounds[0].observations);assert.deepEqual(next.rounds[0].workflow,before.rounds[0].workflow);assert.equal(m.linkRecordIssues(next,'r',[link()]),next);
 assert.deepEqual(m.importArchive(s,next),next);assert.equal(m.importArchive(next,s),next);assert.equal(m.importArchive(next,next),next);assert.deepEqual(proposed(s,s.revision,next),next);
 for(const bad of [link({actor:'Changed'}),link({observationId:'other'}),link({createdAt:'invalid'})])rejectUnchanged(next,s=>m.linkRecordIssues(s,'r',[bad]));
 for(const change of [x=>delete x.rounds[0].issueLinks,x=>x.rounds[0].issueLinks[0].actor='Rewrite']){const bad=structuredClone(next);bad.revision++;change(bad);assert.throws(()=>proposed(next,next.revision,bad));}
 const alternative=m.linkRecordIssues(s,'r',[link({id:'other',url:'https://github.com/fixture/project/issues/13'})]);const merged=m.importArchive(next,alternative);assert.equal(merged.rounds[0].issueLinks.length,2);assert.equal(m.statusOf(merged.rounds[0],'S'),'failed');
 rejectUnchanged(next,s=>m.linkRecordIssues(s,'r',[link(),link({id:'invalid',url:'invalid'})]));
});
test('old archives and persisted conclusion representation stay unchanged until linked',()=>{
 let s=fixture();s=m.record(s,'r',{...observation(s),evidence:'Legacy screenshot path'});assert(!('issueLinks' in s.rounds[0]));assert(!('issues' in testConclusions(s).rounds[0].executions[0]));assert.equal(m.validate(s),s);
 const legacy=structuredClone(s);delete legacy.rounds[0].workflow;m.validate(legacy);const linked=m.linkRecordIssues(legacy,'r',[link()]);assert.equal(testConclusions(linked).rounds[0].verdict,'legacy');assert.deepEqual(linked.rounds[0].observations,legacy.rounds[0].observations);
});
