// Disposable reference adapter for the project integration guide.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const fixture={
  repository:'fixture/workbench',plan:'p',planRevision:4,revision:12,
  targets:{one:{base:'base-one',head:'head-one'},two:{base:'base-two',head:'head-two'}},
  rounds:{
    a:{target:'one',source:'tested-a',revision:8,failed:['A','B','C'],unfinished:['D']},
    older:{target:'one',source:'tested-older',revision:6,failed:['E'],unfinished:[]},
    b:{target:'two',source:'tested-b',revision:11,failed:[],unfinished:['F']}
  }
};

function prepare(snapshot,{target,selectedRound,choice={mode:'auto'},historical=false,scope='focused'}){
  if(!snapshot)throw new Error('Archived snapshot is unavailable');
  const comparison=snapshot.targets[target];
  if(!comparison)throw new Error('Target PR is unavailable in this snapshot');
  const roundId=choice.mode==='round'?choice.id:
    choice.mode==='auto'&&snapshot.rounds[selectedRound]?.target===target?selectedRound:null;
  const round=roundId?snapshot.rounds[roundId]:null;
  if(choice.mode==='round'&&round?.target!==target)throw new Error('Choose a compatible round');
  const response={
    repository:snapshot.repository,plan:snapshot.plan,planRevision:snapshot.planRevision,revision:snapshot.revision,
    target,base:comparison.base,head:comparison.head,mode:choice.mode,baselineRound:roundId,
    baselineSource:round?.source??comparison.base,baselineRevision:round?.revision??null,
    failed:round?.failed??[],unfinished:round?.unfinished??[],historical,scope
  };
  return {...response,previewId:createHash('sha256').update(JSON.stringify(response)).digest('hex')};
}

function fixtureAdapter(live, archived, registerTool){
  let view={target:'one',selectedRound:'a'},open=false;
  const api=request=>prepare(request.historical?archived():live(),request);
  const prepareFromView=(overrides={})=>api({...view,...overrides});
  registerTool?.('prepare_next_round',prepareFromView);
  return {
    api,
    setView(context){view=context;},
    openDialog(){open=true;},
    closeDialog(){open=false;},
    dialog(overrides){assert(open);return prepareFromView(overrides);},
    confirm(previous,request){
      if(previous.historical)throw new Error('Historical preview is read-only');
      const latest=prepareFromView(request);
      if(previous.previewId!==latest.previewId)throw new Error('Preview is stale');
      return latest;
    }
  };
}

test('dialog, API and registered tool share target, candidates and preview inside or outside the dialog',()=>{
  const live=structuredClone(fixture),before=structuredClone(live),registry=new Map();
  const adapter=fixtureAdapter(()=>live,()=>null,registry.set.bind(registry));
  const tool=registry.get('prepare_next_round'),outside=tool();
  assert.deepEqual(outside.failed,['A','B','C']);
  assert.deepEqual(outside.unfinished,['D']);
  assert.equal(outside.baselineSource,'tested-a');
  adapter.openDialog();
  assert.deepEqual(adapter.dialog(),outside);
  assert.deepEqual(tool(),outside);
  assert.deepEqual(adapter.api({target:'one',selectedRound:'a'}),outside);
  const override={choice:{mode:'round',id:'older'}};
  assert.deepEqual(adapter.dialog(override),tool(override));
  assert.equal(tool(override).baselineSource,'tested-older');
  assert.equal(adapter.confirm(tool(override),override).previewId,tool(override).previewId);
  adapter.closeDialog();
  assert.deepEqual(tool(),outside);
  adapter.setView({target:'two',selectedRound:'a'});
  assert.equal(tool().baselineSource,'base-two');
  assert.equal(tool().baselineRound,null);
  assert.deepEqual(tool().failed,[]);
  assert.throws(()=>tool(override),/compatible/);
  const base=tool({choice:{mode:'pr-base'},selectedRound:'b'});
  assert.equal(base.baselineRound,null);
  assert.equal(base.baselineSource,'base-two');
  assert.deepEqual(base.unfinished,[]);
  assert.deepEqual(live,before);
});

test('confirmation rejects target, baseline, saved revision and historical changes without persisting',()=>{
  let live=structuredClone(fixture),archive=structuredClone(fixture);
  archive.revision=8;
  archive.rounds.a.failed=['historic-A'];
  const registry=new Map(),adapter=fixtureAdapter(()=>live,()=>archive,registry.set.bind(registry));
  const tool=registry.get('prepare_next_round'),initial=tool();
  for(const change of [
    data=>{data.targets.one.head='new-head';},
    data=>{data.rounds.a.source='new-tested-source';},
    data=>{data.rounds.a.revision++;},
    data=>{data.rounds.a.failed.push('new-failure');},
    data=>{data.revision++;},
    data=>{data.planRevision++;}
  ]){
    live=structuredClone(fixture);
    change(live);
    const before=structuredClone(live);
    assert.throws(()=>adapter.confirm(initial),/stale/);
    assert.deepEqual(live,before);
  }
  const historical=tool({historical:true});
  assert.deepEqual(historical.failed,['historic-A']);
  assert.equal(historical.revision,8);
  assert.throws(()=>adapter.confirm(historical),/read-only/);
  archive=null;
  assert.throws(()=>tool({historical:true}),/snapshot is unavailable/);
  const withoutRegistry=fixtureAdapter(()=>live,()=>null);
  withoutRegistry.openDialog();
  assert.equal(withoutRegistry.dialog().baselineRound,'a');
});
