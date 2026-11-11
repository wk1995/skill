import * as model from '../assets/workbench/model.mjs';

export function multiChangeArchive() {
  const item=id=>({id,title:id,types:['smoke'],priority:'P1',preconditions:'',steps:'Exercise',expected:'Observe'});
  const plan={id:'p',title:'Shared plan',version:'2.0.0',revision:0,source:'release-sha',build:'release-build',pr:'release',cases:['A','B'].map(item)};
  let state=model.importPlan(model.empty(),plan);
  const create=(id,createdAt,cases)=>model.createRound(state,{id,name:id,createdAt,planId:'p',selection:{
    source:cases.length===2?'full-regression':'issue',planRevision:state.plans[0].revision,cases
  }});
  state=create('release','2026-11-09T00:00:00Z',['A','B']);
  state=model.importPlan(state,{...plan,revision:1,source:'fix-sha',pr:'fix'});
  state=create('fix','2026-11-10T00:00:00Z',['B']);
  return model.importPlan(state,{...plan,revision:2});
}
