export function groupRoundHistory(rounds) {
  const groups = new Map();
  for (const round of rounds) {
    const key = JSON.stringify(round.pr ? ['change', round.pr] : ['source', round.source]);
    if (!groups.has(key)) groups.set(key, {label: round.pr || round.source, rounds: []});
    groups.get(key).rounds.push(round);
  }
  const compare = (a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  return [...groups.values()].map(group => {
    group.rounds.sort(compare);
    return {...group, latest: group.rounds.at(-1)};
  }).sort((a, b) => compare(b.latest, a.latest));
}

export function historyVerdict(report) {
  if (!report || report.verdict === 'legacy') return '无可用结论';
  if (report.executions.some(item => item.dependencyStale)) return '结论证据已过期';
  if (!report.executions.some(item => item.observationId)) return '尚无执行结论';
  if (report.verdict === 'incomplete') return '尚未完成';
  const verdict = {passed:'通过',failed:'未通过',partial:'部分执行',blocked:'阻塞'}[report.verdict];
  return report.lifecycle === 'completed' ? verdict : `${verdict}（轮次未结束）`;
}
