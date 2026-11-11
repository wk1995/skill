// Read-only presentation: attempt history and effective case outcomes have different counts.
import {STATUSES,statusOf} from './model.mjs';
const matches=(item,{query='',type=''})=>(`${item.id} ${item.title}`).toLowerCase().includes(query.trim().toLowerCase())&&(!type||item.types.includes(type));
export function visibleRecords(round,filters={}){
  if(!round)return [];
  return round.observations.filter(record=>{const item=round.cases.find(item=>item.id===record.caseId);return item&&matches(item,filters)&&(!filters.status||record.status===filters.status);});
}
export function visibleCases(definitions,round,filters={},view='cases'){
  const recorded=view==='records'&&filters.status?new Set(visibleRecords(round,filters).map(record=>record.caseId)):null;
  return definitions.filter(item=>matches(item,filters)&&(!filters.status||(recorded?recorded.has(item.id):(round?statusOf(round,item.id):'untested')===filters.status)));
}
export function statistics(definitions,round,view){
  const records=view==='records',values=records?(round?.observations??[]).map(record=>record.status):definitions.map(item=>round?statusOf(round,item.id):'untested');
  return {total:values.length,label:records?'执行记录':'用例总数',counts:Object.fromEntries(STATUSES.map(status=>[status,values.filter(value=>value===status).length]))};
}
