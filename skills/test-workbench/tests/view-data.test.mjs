import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {visibleCases,visibleRecords,statistics} from '../assets/workbench/view-data.mjs';
import * as m from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
const fixture=()=>readFile(new URL('../assets/examples/archive.json',import.meta.url),'utf8').then(JSON.parse);
test('record statistics count attempts while case and summary statistics retain effective outcomes',async()=>{
 let s=await fixture(),r=s.rounds[0],at='2026-10-26T09:00:00Z';s=m.transitionRound(s,r.id,{id:'reopen-view',action:'reopen',from:'completed',actor:'Fixture',at,reason:'Verify fix'});s=m.startExecution(s,r.id,{id:'retry-view',from:'failed',caseId:'PROFILE01',environmentId:'EXAMPLE-ENV',actor:'Fixture',at});s=m.record(s,r.id,{...r.observations[1],id:'fixed-view',status:'passed',tester:'Fixture',recordedAt:at,executedAt:at});r=s.rounds[0];
 const before=structuredClone(s);assert.equal(statistics(r.cases,r,'cases').total,2);assert.equal(statistics(r.cases,r,'cases').counts.passed,2);assert.equal(statistics(r.cases,r,'records').total,3);assert.equal(statistics(r.cases,r,'records').counts.failed,1);
 assert.equal(visibleCases(r.cases,r,{status:'failed'},'cases').length,0);assert.deepEqual(visibleCases(r.cases,r,{status:'failed'},'records').map(x=>x.id),['PROFILE01']);assert.deepEqual(visibleRecords(r,{status:'failed'}).map(x=>x.id),['EXAMPLE-PROFILE-FAIL']);assert.equal(testConclusions(s).rounds[0].counts.failed,0);assert.deepEqual(s,before);
});
test('record filtering composes text, classification and actual historical result without changing conclusions',async()=>{const s=await fixture(),r=s.rounds[0],report=testConclusions(s);assert.equal(visibleRecords(r,{query:'PROFILE',type:'functional',status:'failed'}).length,1);assert.equal(visibleRecords(r,{query:'profile',type:'smoke',status:'failed'}).length,0);assert.equal(visibleRecords(r,{query:'  SIGN IN ',status:'passed'}).length,1);assert.deepEqual(testConclusions(s),report);});
test('definitions and empty rounds produce explicit pending case counts and no fabricated execution records',async()=>{const s=await fixture(),cases=s.plans[0].cases;assert.equal(statistics(cases,null,'cases').counts.untested,2);assert.equal(statistics(cases,null,'records').total,0);assert.deepEqual(visibleRecords(null,{status:'passed'}),[]);assert.deepEqual(visibleCases(cases,null,{status:'passed'}),[]);});
