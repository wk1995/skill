import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as model from '../assets/workbench/model.mjs';
import {unfinishedCandidates, roundOptionLabel} from '../assets/workbench/round-preparation.mjs';

import {multiChangeArchive} from './round-preparation-fixture.mjs';

test('unfinished candidates default to the same frozen change and support explicit same-plan overrides',()=>{
  const state=multiChangeArchive(),plan=state.plans[0],original=structuredClone(state);
  assert.equal(unfinishedCandidates(state,plan).round.id,'release');
  assert.deepEqual(unfinishedCandidates(state,plan).cases,['A','B']);
  assert.deepEqual(unfinishedCandidates(state,plan,'fix').cases,['B']);
  assert.deepEqual(unfinishedCandidates(state,{...plan,pr:'other'}),{round:null,cases:[]});
  assert.deepEqual(unfinishedCandidates(state,plan,'foreign'),{round:null,cases:[]});
  assert.deepEqual(state,original);
});

test('history requires the original owning plan and version while leaving unknown scope explicit',()=>{
  const state=multiChangeArchive(),legacy=structuredClone(state);
  delete legacy.rounds[0].selection;
  assert.match(roundOptionLabel(model.validate(legacy).rounds[0]),/范围分类未知/);
  assert.match(roundOptionLabel(state.rounds[1]),/定向.*2026-11-10.*fix.*1 用例/);
  for(const broken of [{...state,plans:[]},{...state,plans:[{...state.plans[0],version:'wrong'}]}]){
    const before=structuredClone(broken);
    assert.throws(()=>model.importArchive(model.empty(),broken),/Plan not found|version must match/);
    assert.deepEqual(broken,before);
  }
});
