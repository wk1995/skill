export const DEPENDENCIES={field:'case.dependsOn',mode:'all',scope:'same-round-and-environment',requiredState:'passed',freshness:'A started execution pins prerequisite observation IDs; upstream retest/change makes old dependent passes stale. No automatic history rewrite.'};
const require=(ok,message)=>{if(!ok)throw new Error(message);};
export function validateDependencies(item) {
  if(item.dependsOn===undefined)return;
  require(Array.isArray(item.dependsOn)&&item.dependsOn.every(id=>typeof id==='string'&&id.trim()),'dependsOn: case ID array required');
  require(new Set(item.dependsOn).size===item.dependsOn.length,'dependsOn: duplicate prerequisite');
  require(!item.dependsOn.includes(item.id),'dependsOn: self dependency');
}
export function orderCases(cases) {
  const ids=new Set(cases.map(item=>item.id));
  for(const item of cases){validateDependencies(item);for(const id of item.dependsOn??[])require(ids.has(id),`Dependency case not found: ${id}`);}
  const pending=[...cases],ordered=[],done=new Set();
  while(pending.length) {
    const index=pending.findIndex(item=>(item.dependsOn??[]).every(id=>done.has(id)));
    require(index!==-1,'dependsOn: cyclic dependency');
    const [item]=pending.splice(index,1);ordered.push(item);done.add(item.id);
  }
  return ordered;
}
export function dependencyViews(cases,current,environmentId) {
  const views=new Map();
  for(const item of orderCases(cases)) {
    const execution=current(item.id,environmentId),deps=item.dependsOn??[];
    const unmetDependencies=deps.filter(id=>!views.get(id).validPass).map(id=>{
      const parent=views.get(id);return {caseId:id,state:parent.state,observationId:parent.observationId,unresolvedFailureId:parent.unresolvedFailureId,dependencyStale:parent.dependencyStale};
    });
    const currentEvidence=deps.map(caseId=>({caseId,observationId:views.get(caseId).observationId}));
    const dependenciesSatisfied=unmetDependencies.length===0;
    const dependencyStale=Boolean(deps.length&&execution.attemptId&&(!dependenciesSatisfied||JSON.stringify(execution.dependencyEvidence??[])!==JSON.stringify(currentEvidence)));
    views.set(item.id,{...execution,dependenciesSatisfied,unmetDependencies,currentEvidence,dependencyStale,validPass:execution.state===DEPENDENCIES.requiredState&&!execution.unresolvedFailureId&&!dependencyStale});
  }
  return views;
}
