import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as m from '../assets/workbench/model.mjs';
const time='2026-10-22T06:00:00Z';
const caseOf=id=>({id,title:id,priority:'P0',types:['smoke','functional'],preconditions:'Ready',steps:'Select this exact sentence.',expected:'Expected result'});
const plan=()=>({id:'p',revision:0,version:'v1',title:'Plan',source:'sha',build:'',pr:'',cases:[caseOf('A'),caseOf('B')]});
function fixture(){let state=m.importPlan(m.empty(),plan());return m.createRound(state,{id:'r',name:'Round',planId:'p',createdAt:time});}
const event=(id,kind='comment',extra={})=>({id,kind,author:'Tester',body:kind==='comment'?'A review comment':'',createdAt:time,...extra});
const note=(extra={})=>({id:'n',planId:'p',roundId:'r',caseId:'A',origin:'web',target:{field:'steps',quote:'exact sentence'},event:event('e1'),...extra});
function rejects(state,action,pattern){const before=structuredClone(state);assert.throws(()=>action(state),pattern);assert.deepEqual(state,before);}
test('web and native-origin annotations pin context without requiring a device or modifying outcomes',()=>{
  const initial=fixture(),round=structuredClone(initial.rounds[0]);
  let state=m.addAnnotation(initial,note());state=m.addAnnotation(state,note({id:'native',origin:'browser',event:event('native-first')}));
  assert.equal(state.annotations[1].origin,'browser');assert.equal(state.annotations[0].context.source,'sha');
  assert.deepEqual(state.rounds[0],round);assert.equal(m.statusOf(state.rounds[0],'A'),'untested');assert.equal(initial.annotations.length,0);
});
test('creation rejects invalid content, targets, quotes, duplicate IDs and stale snapshots',()=>{
  const state=fixture();
  const bad=[{event:event('bad','resolve')},{event:event('bad','comment',{author:''})},{event:event('bad','comment',{body:' '})},{target:{field:'steps',quote:'not present'}},{target:{field:'unknown',quote:''}},{caseId:'missing'},{roundId:'missing'},{observationId:'missing'},{origin:'unknown'}];
  for(const extra of bad)rejects(state,s=>m.addAnnotation(s,note(extra)));
  const context=m.annotationContext(state,{planId:'p',caseId:'A'});
  const changed=m.editCase(state,'p',{...plan().cases[0],steps:'Changed'});
  rejects(changed,s=>m.addAnnotation(s,note({roundId:'',expectedContext:context})),/definition changed/);
  const created=m.addAnnotation(state,note());rejects(created,s=>m.addAnnotation(s,note()),/already exists/);
});
test('reply, resolve, repeated resolve and reopen append events and preserve the original comment',()=>{
  let state=m.addAnnotation(fixture(),note());const original=structuredClone(state.annotations[0].events[0]);
  state=m.addAnnotationEvent(state,'n',event('reply'));state=m.addAnnotationEvent(state,'n',event('resolved','resolve'));
  assert.equal(m.annotationStatus(state.annotations[0]),'resolved');
  assert.equal(m.addAnnotationEvent(state,'n',event('resolved','resolve')),state);
  assert.equal(m.addAnnotationEvent(state,'n',event('resolve-again','resolve')),state);
  rejects(state,s=>m.addAnnotationEvent(s,'n',event('resolve-invalid','resolve',{author:''})),/author/);
  state=m.addAnnotationEvent(state,'n',event('reopened','reopen',{createdAt:'2026-10-22T06:01:00Z'}));
  assert.equal(m.annotationStatus(state.annotations[0]),'open');assert.deepEqual(state.annotations[0].events[0],original);
  rejects(state,s=>m.addAnnotationEvent(s,'n',event('reply','comment',{body:'rewrite'})),/Conflicting/);
  rejects(state,s=>m.addAnnotationEvent(s,'n',event('bad','delete')),/event kind/);
});
test('library annotation snapshots survive definition changes and case removal',()=>{
  let state=m.addAnnotation(fixture(),note({roundId:''}));const old=structuredClone(state.annotations[0]);
  state=m.importPlan(state,{...plan(),revision:1,source:'new-sha',cases:[caseOf('B')]});
  assert.deepEqual(state.annotations[0],old);assert.equal(m.annotationsFor(state,{planId:'p',roundId:''}).length,1);
  assert.equal(m.annotationsFor(state,{planId:'p',roundId:'r'}).length,0);
});
test('observation annotations remain bound to the correct round and case',()=>{
  let state=fixture();const env={id:'env',label:'Device',kind:'browser',configuration:'Config'};
  state=m.registerEnvironment(state,env);state=m.attachEnvironment(state,'r','env');
  const observation={id:'o',caseId:'B',environmentId:'env',environment:env,status:'failed',executedAt:time,recordedAt:time,tester:'Tester',notes:'Actual failure',evidence:'screenshot'};
  state=m.record(state,'r',observation);const before=structuredClone(state.rounds[0]);
  rejects(state,s=>m.addAnnotation(s,note({observationId:'o'})),/another case/);
  state=m.addAnnotation(state,note({caseId:'B',observationId:'o',target:{field:'observation',quote:'Actual failure'}}));
  assert.deepEqual(state.rounds[0],before);assert.equal(m.statusOf(state.rounds[0],'B'),'failed');
  assert.equal(m.annotationsFor(state,{planId:'p',roundId:'r',caseId:'B',observationId:'o'}).length,1);
  assert.equal(m.annotationsFor(state,{planId:'p',roundId:'r',caseId:'A'}).length,0);
});
test('old archives without annotations remain readable and cannot erase local annotations',()=>{
  const legacy=fixture();delete legacy.annotations;m.validate(legacy);
  const local=m.addAnnotation(legacy,note());assert.equal(local.annotations.length,1);
  assert.equal(m.importArchive(local,legacy),local);
  const restored=m.importArchive(m.empty(),JSON.parse(JSON.stringify(local)));assert.deepEqual(restored.annotations,local.annotations);
  rejects(local,s=>m.importArchive(s,{...legacy,annotations:null}),/array required/);
});
test('annotation archive merge is idempotent and rejects conflicting immutable context or events atomically',()=>{
  const base=m.addAnnotation(fixture(),note());
  const left=m.addAnnotationEvent(base,'n',event('left'));
  const right=m.addAnnotationEvent(base,'n',event('right','resolve',{createdAt:'2026-10-22T06:02:00Z'}));
  const merged=m.importArchive(left,right);assert.equal(merged.annotations[0].events.length,3);assert.equal(m.annotationStatus(merged.annotations[0]),'resolved');
  assert.equal(m.importArchive(merged,right),merged);
  for(const edit of [archive=>archive.annotations[0].origin='browser',archive=>archive.annotations[0].events[0].body='rewritten']){
    const incoming=structuredClone(merged);edit(incoming);rejects(merged,s=>m.importArchive(s,incoming),/Conflicting/);
  }
  const invalid=structuredClone(merged);invalid.annotations.push({...structuredClone(invalid.annotations[0]),id:'bad',roundId:'missing'});
  rejects(merged,s=>m.importArchive(s,invalid),/round/);
});
test('native/browser event ordering is independent of archive merge order and JSON text remains inert',()=>{
  let state=m.addAnnotation(fixture(),note({event:event('e1','comment',{body:'<img src=x onerror=alert(1)>'})}));
  state=m.addAnnotationEvent(state,'n',event('resolved','resolve',{createdAt:'2026-10-22T06:01:00Z'}));
  state=m.addAnnotationEvent(state,'n',event('reopened','reopen',{createdAt:'2026-10-22T06:02:00Z'}));
  const reversed={...state.annotations[0],events:[state.annotations[0].events[0],...state.annotations[0].events.slice(1).reverse()]};
  assert.equal(m.annotationStatus(reversed),'open');assert.deepEqual(m.validate(JSON.parse(JSON.stringify(state))),state);
  const tied={...reversed,events:[event('root'),event('a-reopen','reopen'),event('Z-resolve','resolve')]};
  assert.equal(m.annotationStatus(tied),'open');assert.deepEqual(m.orderedAnnotationEvents(tied).map(item=>item.id),['Z-resolve','a-reopen','root']);
});
