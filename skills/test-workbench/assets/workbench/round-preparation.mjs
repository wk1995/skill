import {roundsFor, statusOf} from './model.mjs';

function sameChange(plan, round) {
  // The frozen PR identifies a change across builds. Without a PR, require
  // the exact tested source instead of guessing from timestamps.
  return plan.pr ? round.pr === plan.pr : !round.pr && round.source === plan.source;
}

export function unfinishedCandidates(state, plan, sourceId = '') {
  const rounds = roundsFor(state, plan.id);
  const round = sourceId ? rounds.find(item => item.id === sourceId) : rounds.filter(item => sameChange(plan, item))
    .sort((a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)).at(-1);
  if (!round) return {round: null, cases: []};
  const currentIds = new Set(plan.cases.map(item => item.id));
  const cases = round.cases.filter(item => currentIds.has(item.id) && statusOf(round, item.id) !== 'passed').map(item => item.id);
  return {round, cases};
}

export function roundOptionLabel(round) {
  const scope = !round.selection ? '范围分类未知' : round.selection.source === 'full-regression' ? '完整回归' : '定向轮次';
  return `${round.name} · ${scope} · ${round.createdAt} · ${round.pr || round.source || '变更未知'} · ${round.cases.length} 用例`;
}
