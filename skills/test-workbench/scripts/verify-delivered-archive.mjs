#!/usr/bin/env node
import {readFile, realpath} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {FileSource, GitHubSource, canonical, require} from './workspace-sources.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';

const text=value=>typeof value==='string'&&value.trim().length>0;
const strings=value=>Array.isArray(value)&&value.every(text)&&new Set(value).size===value.length;
const equal=(a,b)=>canonical(a)===canonical(b);
const fields=['planId','version','source','build'];

export async function verifyDeliveredArchive(source, expected){
  require(Array.isArray(expected)&&expected.length>0,'Expected a nonempty array of shared rounds');
  const ids=new Set();
  for(const entry of expected){
    require(entry&&text(entry.roundId)&&!ids.has(entry.roundId)&&fields.every(field=>field==='build'?typeof entry.build==='string':text(entry[field]))&&
      strings(entry.scope)&&entry.scope.length&&strings(entry.evidence)&&text(entry.verdict)&&
      (entry.observationId===undefined||text(entry.observationId)),'Invalid or duplicate expected round');
    ids.add(entry.roundId);
  }
  const description=`Expected rounds: ${[...ids].join(', ')}`;
  let loaded;
  try{loaded=await source.read();}catch(error){throw new Error(`${description}. ${error.message}`,{cause:error});}
  const {state,info}=loaded;
  require(info.initialized,`${description}. ${info.mode==='github-issues'?'Workspace index or publication is missing':'Committed workspace pointer is missing'}`);
  require(info.mode!=='repository-files'||!info.dirty,`${description}. Test data must match committed files in a clean checkout`);
  const conclusions=new Map(testConclusions(state).rounds.map(report=>[report.roundId,report]));
  const rounds=expected.map(entry=>{
    const label=`Round ${entry.roundId}`,round=state.rounds.find(item=>item.id===entry.roundId);
    require(round,`${label} is missing from the published archive`);
    for(const field of fields)require(round[field]===entry[field],`${label}: ${field} differs`);
    require(equal(round.cases.map(item=>item.id),entry.scope),`${label}: frozen scope differs`);
    require(conclusions.get(round.id)?.verdict===entry.verdict,`${label}: conclusion differs`);
    const evidence=[...new Set([...round.observations.map(item=>item.evidence).filter(Boolean),...(round.issueLinks??[]).map(item=>item.url)])].sort();
    require(equal(evidence,[...entry.evidence].sort()),`${label}: evidence references differ`);
    const link=new URLSearchParams({plan:round.planId,round:round.id,view:'summary'});
    if(entry.observationId){
      const observation=round.observations.find(item=>item.id===entry.observationId);
      require(observation,`${label}: observation ${entry.observationId} is missing`);
      link.set('view','records');link.set('case',observation.caseId);link.set('environment',observation.environmentId);link.set('observation',observation.id);
    }
    return {roundId:round.id,source:round.source,scope:entry.scope,verdict:entry.verdict,link:'#'+link};
  });
  return {mode:info.mode,revision:state.revision,...(info.head?{head:info.head}:{issue:info.issue}),rounds};
}

async function main(args){
  if(args.length===1&&args[0]==='--help'){
    console.log('Read-only verification. Supply --expect FILE and either --repo-root ROOT [--data-dir DIR] or --repo OWNER/REPO [--hostname HOST] [--issue NUMBER]. Both modes accept --workspace NAME.');
    return;
  }
  const values=Object.create(null);
  const supported=new Set(['--expect','--repo','--hostname','--workspace','--issue','--repo-root','--data-dir']);
  for(let i=0;i<args.length;i+=2){
    const [flag,value]=[args[i],args[i+1]],key=flag.slice(2);
    require(supported.has(flag)&&text(value)&&!value.startsWith('--')&&!Object.hasOwn(values,key),`Invalid, missing or repeated option: ${flag}`);
    values[key]=value;
  }
  require(values.expect&&Boolean(values.repo)!==Boolean(values['repo-root']),'Supply --expect and exactly one of --repo or --repo-root');
  require(values.repo?!values['data-dir']:!values.hostname&&!values.issue,'Source options do not match the selected mode');
  require(values.issue===undefined||/^\d+$/.test(values.issue),'Invalid Issue number');
  const expected=JSON.parse(await readFile(values.expect,'utf8'));
  const source=values.repo?
    new GitHubSource({repo:values.repo,hostname:values.hostname,workspace:values.workspace,issue:values.issue===undefined?undefined:Number(values.issue)}):
    new FileSource({repoRoot:values['repo-root'],dataDir:values['data-dir'],workspace:values.workspace});
  console.log(JSON.stringify(await verifyDeliveredArchive(source,expected),null,2));
}
if(process.argv[1]&&await realpath(process.argv[1]).catch(()=>null)===fileURLToPath(import.meta.url)){
  main(process.argv.slice(2)).catch(error=>{console.error(error.message);process.exitCode=1;});
}
