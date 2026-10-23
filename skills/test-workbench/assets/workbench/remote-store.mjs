import {validate} from './model.mjs';
async function request(store,endpoint,method='GET',body){
  let response;try{response=await fetch(endpoint,{method,cache:'no-store',headers:body?{'Content-Type':'application/json','X-Testflow-Session':store.session}:{},...(body?{body:JSON.stringify(body)}:{})});}catch{throw new Error('无法连接主数据源服务；内容尚未确认保存，请保留草稿并重试');}
  const result=await response.json().catch(()=>({error:'请使用 workbench-server.mjs 启动工作台；不会自动切换到浏览器存储'}));
  if(!response.ok)throw new Error(result.error==='Missing session token'?'本机服务连接已过期；请保留草稿，重新载入网页并核对数据源':result.error??'主数据源操作失败；请保留草稿');return result;
}
export async function openRemote(){const config=await request({},'/api/config');if(typeof config.session!=='string'||!['github-issues','repository-files'].includes(config.mode))throw new Error('主数据源配置无效');return {remote:true,session:config.session,info:{mode:config.mode}};}
function accept(store,result){const state=validate(result.state);const identity=JSON.stringify([result.info?.mode,result.info?.repository,result.info?.path??'',result.info?.workspace]);if(result.info?.mode!==store.info.mode||store.identity&&store.identity!==identity)throw new Error('主数据源发生变化；请保留草稿并重新连接核对');store.identity=identity;store.info=result.info;return state;}
export async function readRemote(store){return accept(store,await request(store,'/api/workspace'));}
export async function updateRemote(store,expectedRevision,action){const current=await readRemote(store);if(current.revision!==expectedRevision)throw new Error('数据已变化，请刷新核对后再保存');const candidate=validate(action(structuredClone(current)));return accept(store,await request(store,'/api/workspace','PUT',{expectedRevision,state:candidate}));}
export async function initializeSource(store){if(!store?.remote)throw new Error('本地预览不能初始化主数据源');return accept(store,await request(store,'/api/initialize','POST',{}));}
export async function commitSource(store,expectedRevision){if(!store?.remote)throw new Error('本地预览不能提交 Git');return accept(store,await request(store,'/api/commit','POST',{expectedRevision}));}
