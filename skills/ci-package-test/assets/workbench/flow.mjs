import {orderCases} from './dependencies.mjs';
import {inspectWorkflow} from './workflow.mjs';
import {nextTest, validateTargets} from './routing.mjs';
import {locationHint} from './test-location.mjs';
// Read-only projection used by both browser rendering and AI export.
export function projectFlow(context,{caseId='',environmentId=''}={}) {
  const cases=orderCases(context.cases);validateTargets(cases);
  if(caseId&&!cases.some(item=>item.id===caseId))throw new Error('Flow case not found');
  const round=Object.hasOwn(context,'planId')?context:null;
  const attached=Boolean(round?.environments.some(env=>env.id===environmentId));
  const mode=!round?'definition':!round.workflow?'legacy':!attached?'environment-required':'managed';
  const executions=mode==='managed'?inspectWorkflow(round).executions.filter(entry=>entry.environmentId===environmentId):[];
  const byId=new Map(executions.map(entry=>[entry.caseId,entry]));
  const advice=mode==='managed'?new Map(cases.map(item=>[item.id,nextTest(round,item.id,environmentId)])):new Map();
  const depths=new Map(),rows=new Map();
  const nodes=cases.map(item=>{
    const depth=Math.max(0,...(item.dependsOn??[]).map(id=>depths.get(id)+1));depths.set(item.id,depth);
    const row=rows.get(depth)??0;rows.set(depth,row+1);
    const execution=byId.get(item.id);
    return {caseId:item.id,title:item.title,state:execution?.state??null,dependenciesSatisfied:execution?.dependenciesSatisfied??null,
      unmetDependencies:structuredClone(execution?.unmetDependencies??[]),dependencyStale:execution?.dependencyStale??false,
      unresolvedFailureId:execution?.unresolvedFailureId??null,validPass:execution?.validPass??false,
      testLocation:locationHint(item),x:40+depth*320,y:40+row*180,width:232,height:132};
  });
  const edges=[];
  for(const item of cases) {
    for(const from of item.dependsOn??[])edges.push({kind:'dependency',from,to:item.id,outcomes:[],active:false});
    const routes=new Map();
    for(const [outcome,route] of Object.entries(item.next??{})) {
      if(!['test','retry'].includes(route.action))continue;
      if(!routes.has(route.caseId))routes.set(route.caseId,[]);routes.get(route.caseId).push(outcome);
    }
    for(const [to,outcomes] of routes) {
      const actual=advice.get(item.id);
      const active=Boolean(actual?.available&&outcomes.includes(byId.get(item.id).state)&&['test','retry'].includes(actual.action)&&actual.targetCaseId===to);
      edges.push({kind:'next',from:item.id,to,outcomes,active});
    }
  }
  return {mode,roundId:round?.id??null,environmentId:mode==='managed'?environmentId:null,caseId,
    nextTest:advice.get(caseId)??null,nodes,edges,
    width:Math.max(520,...nodes.map(node=>node.x+node.width+180)),height:Math.max(220,...nodes.map(node=>node.y+node.height+35))};
}
