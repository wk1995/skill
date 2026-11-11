import {test} from 'node:test';
import assert from 'node:assert/strict';
import {groupRoundHistory, historyVerdict} from '../assets/workbench/round-history.mjs';

test('round history compares zoned instants, breaks ties by stable ID and separates unlinked sources',()=>{
  const rounds=[
    {id:'z',pr:'change',source:'a',createdAt:'2026-11-10T09:00:00+08:00'},
    {id:'a',pr:'change',source:'b',createdAt:'2026-11-10T01:00:00Z'},
    {id:'c',pr:'change',source:'c',createdAt:'2026-11-10T01:30:00Z'},
    {id:'l',pr:'',source:'change',createdAt:'2026-11-10T02:00:00Z'}
  ];
  const before=structuredClone(rounds),groups=groupRoundHistory(rounds);
  assert.deepEqual(groups.map(group=>group.rounds.map(round=>round.id)),[['l'],['a','z','c']]);
  assert.equal(groups[1].latest.id,'c');
  assert.deepEqual(rounds,before);
});

test('latest state is evaluated from its own report, including no execution, unfinished and stale evidence',()=>{
  assert.equal(historyVerdict(undefined),'无可用结论');
  assert.equal(historyVerdict({verdict:'legacy'}),'无可用结论');
  assert.equal(historyVerdict({verdict:'incomplete',executions:[{observationId:null}]}),'尚无执行结论');
  assert.equal(historyVerdict({verdict:'incomplete',executions:[{observationId:'previous'}]}),'尚未完成');
  assert.equal(historyVerdict({verdict:'failed',lifecycle:'running',executions:[{observationId:'failure'}]}),'未通过（轮次未结束）');
  assert.equal(historyVerdict({verdict:'blocked',executions:[{observationId:'previous',dependencyStale:true}]}),'结论证据已过期');
});
