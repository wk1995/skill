#!/usr/bin/env node
// Read-only format/semantic validation, sharing the actual webpage/source validators.
import * as fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {validate,validatePlan} from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
export function validateTestData(data,{kind='archive',conclusions}={}) {
  if(!['archive','plan'].includes(kind))throw new Error('Unsupported testing data kind');
  if(kind==='plan'){
    if(conclusions!==undefined)throw new Error('Conclusions require their supporting archive');
    validatePlan(data);return {format:'ci-package-test/validation',version:1,valid:true,kind,planId:data.id,cases:data.cases.length};
  }
  validate(data);const derived=testConclusions(data);
  if(conclusions!==undefined&&!isDeepStrictEqual(conclusions,derived))throw new Error('Test conclusions do not match the exact archive revision and records');
  return {format:'ci-package-test/validation',version:1,valid:true,kind,schemaVersion:data.schemaVersion,revision:data.revision,plans:data.plans.length,rounds:data.rounds.length,conclusions:conclusions===undefined?'derived':'verified'};
}
export function options(args){
  const result={};
  for(let i=0;i<args.length;i++){
    const fields={'--archive':'archive','--plan':'plan','--conclusions':'conclusions'},key=Object.hasOwn(fields,args[i])?fields[args[i]]:null;
    if(!key||Object.hasOwn(result,key)||!args[i+1]||args[i+1].startsWith('--'))throw new Error(`Unknown, duplicate or missing option: ${args[i]}`);
    result[key]=args[++i];
  }
  if(Boolean(result.archive)===Boolean(result.plan)||result.plan&&result.conclusions)throw new Error('Specify --archive FILE [--conclusions FILE], or --plan FILE');
  return result;
}
async function readJSON(file){let value;try{value=JSON.parse(await fs.readFile(file,'utf8'));}catch(error){throw new Error(`Cannot read JSON ${file}: ${error.message}`);}return value;}
export async function main(args=process.argv.slice(2)){
  if(args.length===1&&args[0]==='--help'){console.log('Read-only validation; Node.js18+. No Git, gh, network or persistence.\nnode scripts/validate-test-data.mjs --plan plan.json\nnode scripts/validate-test-data.mjs --archive archive.json [--conclusions conclusions.json]\nValidate files from an explicit export; never edit source generation pointers or Issue packets by hand.');return;}
  const config=options(args),data=await readJSON(config.archive??config.plan),conclusions=config.conclusions?await readJSON(config.conclusions):undefined;
  console.log(JSON.stringify(validateTestData(data,{kind:config.archive?'archive':'plan',conclusions})));
}
if(process.argv[1]&&await fs.realpath(process.argv[1]).catch(()=>null)===fileURLToPath(import.meta.url))main().catch(error=>{console.error(error.message);process.exitCode=1;});
