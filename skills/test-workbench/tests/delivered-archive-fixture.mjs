import os from 'node:os';
import * as model from '../assets/workbench/model.mjs';
import {command} from '../scripts/workspace-sources.mjs';

export async function initFixtureRepo(root){
  await command('git',['init','-q','-b','main',root]);
  for(const [key,value] of [['user.name','Fixture'],['user.email','fixture@example.invalid'],['commit.gpgsign','false'],['core.hooksPath',os.devnull]]){
    await command('git',['-C',root,'config',key,value]);
  }
  await command('git',['-C',root,'commit','--allow-empty','-qm','Initial']);
}

export function archiveFixture(){
  const item={id:'A',title:'Original case',types:['smoke'],priority:'P1',preconditions:'',steps:'Original procedure',expected:'Observe'};
  const plan={id:'p',title:'Fixture',revision:0,version:'2.0.0',source:'old-sha',build:'build-1',pr:'change',cases:[item]};
  const definitions=model.importPlan(model.empty(),plan);
  const at='2026-11-10T08:00:00Z',actor='Fixture',environment={id:'e',label:'Browser',kind:'browser',configuration:'Fixture'};
  const old={id:'old',name:'Original round',planId:'p',createdAt:at,selection:{source:'issue',planRevision:0,cases:['A']}};
  let state=model.registerEnvironment(model.createRound(definitions,old),environment);
  state=model.attachEnvironment(state,'old','e');
  for(const [action,from] of [['prepare','draft'],['begin','ready']])state=model.transitionRound(state,'old',{id:action,action,from,actor,at});
  state=model.startExecution(state,'old',{id:'start',from:'untested',caseId:'A',environmentId:'e',actor,at});
  const evidence='https://github.com/example/workbench/issues/17';
  state=model.recordBatch(state,'old',[{id:'original-observation',caseId:'A',environmentId:'e',environment,status:'failed',
    executedAt:at,recordedAt:at,tester:actor,notes:'Original failure',evidence:''}],
    [{id:'evidence-link',observationId:'original-observation',url:evidence,createdAt:at,actor}]);
  state=model.transitionRound(state,'old',{id:'complete',action:'complete',from:'running',actor,at});
  state=model.importPlan(state,{...plan,revision:1,source:'new-sha',cases:[{...item,title:'New case'}]});
  state=model.createRound(state,{...old,id:'new',name:'New round',selection:{...old.selection,planRevision:1}});
  return {definitions:{...definitions,revision:1},state:{...state,revision:2},expected:[{
    roundId:'old',planId:'p',version:'2.0.0',source:'old-sha',build:'build-1',scope:['A'],verdict:'failed',
    evidence:[evidence],observationId:'original-observation'
  }]};
}
