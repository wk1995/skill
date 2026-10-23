import {recordIssues} from './issue-links.mjs';
import {inspectWorkflow,CONTRACT} from './workflow.mjs';
export function testConclusions(archive){
  return {format:'ci-package-test/conclusions',version:1,archiveRevision:archive.revision,rounds:archive.rounds.map(round=>{
    const context={roundId:round.id,planId:round.planId,version:round.version,source:round.source,build:round.build,pr:round.pr};
    if(!round.workflow)return {...context,lifecycle:'legacy',verdict:'legacy',counts:null,executions:[],meaning:'Legacy observations retained; no managed conclusion inferred.'};
    const view=inspectWorkflow(round),executions=view.executions.map(item=>({caseId:item.caseId,environmentId:item.environmentId,phase:item.state,result:item.unresolvedFailureId?'failed':item.dependencyStale&&['passed','running'].includes(item.state)?'blocked':item.state,observationId:item.observationId,unresolvedFailureId:item.unresolvedFailureId,dependencyStale:item.dependencyStale,...issueProjection(round,item)}));
    const counts=Object.fromEntries(CONTRACT.summaryPriority.map(status=>[status,executions.filter(item=>item.result===status).length]));
    const verdict=counts.failed?'failed':counts.blocked?'blocked':counts.partial?'partial':view.state!=='completed'?'incomplete':executions.length&&counts.passed===executions.length?'passed':'incomplete';
    return {...context,lifecycle:view.state,verdict,counts,executions,meaning:'Derived from recorded evidence only; incomplete, skipped or missing coverage is not a pass. This is not release approval.'};
  })};
}

function issueProjection(round,item){const issues=[...new Set([item.observationId,item.unresolvedFailureId].filter(Boolean).flatMap(id=>recordIssues(round,id)))];return issues.length?{issues}:{};}
