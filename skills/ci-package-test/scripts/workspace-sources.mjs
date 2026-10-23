import * as fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import {empty,validate,importArchive} from '../assets/workbench/model.mjs';
import {testConclusions} from '../assets/workbench/conclusions.mjs';
export const FORMAT='ci-package-test/source-1';
export const require=(ok,message)=>{if(!ok)throw new Error(message);};
export function canonical(value){return JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);}
const digest=value=>createHash('sha256').update(canonical(value)).digest('hex');
export function proposed(current,expected,candidate){
  validate(current);validate(candidate);
  require(Number.isSafeInteger(expected)&&expected===current.revision,'数据已变化，请刷新核对后再保存');
  if(canonical(current)===canonical(candidate))return current;
  require(candidate.revision===current.revision+1,'Invalid update revision');
  const merged=structuredClone(importArchive(current,candidate));merged.revision=candidate.revision;
  require(canonical(merged)===canonical(candidate),'不能删除或改写历史、环境或批注；请追加记录');
  return candidate;
}
export function command(executable,args,{cwd,input,env=process.env}={}){
  return new Promise((resolve,reject)=>{
    const commandEnv={...env,GH_PROMPT_DISABLED:'1',GIT_TERMINAL_PROMPT:'0'};
    if(executable==='git'){for(const key of ['GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_NAMESPACE','GIT_GLOB_PATHSPECS','GIT_NOGLOB_PATHSPECS','GIT_ICASE_PATHSPECS'])delete commandEnv[key];commandEnv.GIT_LITERAL_PATHSPECS='1';}
    const child=spawn(executable,args,{cwd,stdio:['pipe','pipe','pipe'],env:commandEnv});
    child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');
    let out='',err='',failure;const timer=setTimeout(()=>{failure=new Error(`${executable}: command timed out; inspect the source before retrying`);child.kill();},30000);
    child.stdout.on('data',data=>{out+=data;if(out.length>32*1024*1024){failure=new Error('Command output too large');child.kill();}});child.stderr.on('data',data=>{err=(err+data).slice(-4000);});
    child.on('error',error=>{failure=new Error(`${executable} unavailable: ${error.code}`);});
    child.on('close',code=>{clearTimeout(timer);failure?reject(failure):code===0?resolve(out):reject(new Error(`${executable}: ${err.trim()||`exit ${code}`}`));});
    child.stdin.on('error',()=>{});child.stdin.end(input);
  });
}
const packet=value=>`<!-- ${FORMAT} -->\n\n\`\`\`json\n${JSON.stringify(value)}\n\`\`\`\n`;
function unpack(body){const match=typeof body==='string'&&body.match(/^<!-- ci-package-test\/source-1 -->\n\n```json\n([^\n]+)\n```\n$/);require(match,'Source document is missing or malformed');return JSON.parse(match[1]);}
const number=value=>Number.isSafeInteger(value)&&value>0;
export class GitHubSource{
  constructor({repo,hostname='github.com',workspace='default',issue,run=command}){
    require(/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo??''),'GitHub 模式需要 --repo OWNER/REPO');
    require(/^[A-Za-z0-9.-]+$/.test(hostname)&&!hostname.startsWith('-'),'Invalid GitHub hostname');
    require(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(workspace),'Invalid workspace name');
    require(issue===undefined||number(issue),'Invalid workspace Issue number');
    Object.assign(this,{repo,hostname,workspace,index:issue,run,actor:null});
  }
  async api(method,endpoint,data){const args=['api','--hostname',this.hostname,'--method',method,endpoint];if(data)args.push('--input','-');return JSON.parse(await this.run('gh',args,{input:data?JSON.stringify(data):undefined}));}
  async preflight(){const user=await this.api('GET','user');require(typeof user.login==='string'&&user.login,'无法确认 gh 当前账号');require(!this.actor||this.actor===user.login,'gh 账号已变化；请重启服务并核对目标');this.actor=user.login;const repo=await this.api('GET',`repos/${this.repo}`);require(repo.full_name?.toLowerCase()===this.repo.toLowerCase()&&repo.has_issues!==false,'Repository identity mismatch or Issues disabled');}
  async issues(){const result=[];for(let page=1;;page++){const batch=await this.api('GET',`repos/${this.repo}/issues?state=all&per_page=100&page=${page}`);require(Array.isArray(batch),'Invalid Issues list');result.push(...batch.filter(item=>!item.pull_request));if(batch.length<100)return result;}}
  identity(issue,kind,key){if(issue.pull_request)return false;try{const data=unpack(issue.body);return data.format===FORMAT&&data.workspace===this.workspace&&data.kind===kind&&(key===undefined||data.key===key);}catch{return false;}}
  async indexIssue(){
    if(!this.index){const matches=(await this.issues()).filter(item=>this.identity(item,'index'));require(matches.length<=1,'发现多个工作台索引，请使用 --issue 明确选择');if(!matches.length)return null;this.index=matches[0].number;}
    const issue=await this.api('GET',`repos/${this.repo}/issues/${this.index}`);require(this.identity(issue,'index'),'指定 Issue 不是此工作台索引');return issue;
  }
  async #entity(key,title){const matches=(this.inventory??await this.issues()).filter(item=>this.identity(item,'entity',key));require(matches.length<=1,'Duplicate entity Issues; inspect before retrying');if(matches.length)return matches[0];
    const result=await this.api('POST',`repos/${this.repo}/issues`,{title:title.slice(0,180),body:packet({format:FORMAT,workspace:this.workspace,kind:'entity',key})});require(number(result.number)&&result.user?.login===this.actor,'Issue write identity uncertain; inspect before retrying');this.inventory?.push(result);return result;
  }
  async #document(issueNumber,key,value,old){
    if(old?.digest===digest(value))return old;
    const data=canonical(value),parts=[];const total=Math.max(1,Math.ceil(data.length/10000)),generation=randomUUID();
    for(let part=0;part<total;part++){
      const body=packet({format:FORMAT,workspace:this.workspace,key,generation,part,total,data:data.slice(part*10000,(part+1)*10000)});
      const result=await this.api('POST',`repos/${this.repo}/issues/${issueNumber}/comments`,{body});
      require(number(result.id)&&result.user?.login===this.actor,'Comment write identity uncertain; inspect before retrying');parts.push(result.id);
    }
    const ref={key,issueNumber,comments:parts,digest:digest(value)};require(canonical(await this.readDocument(ref))===canonical(value),'Source document read-back mismatch');return ref;
  }
  async readDocument(ref){
    require(ref&&typeof ref.key==='string'&&number(ref.issueNumber)&&Array.isArray(ref.comments)&&ref.comments.length>0&&ref.comments.every(number)&&new Set(ref.comments).size===ref.comments.length,'Invalid source reference');
    let data='',generation;
    for(const [part,id] of ref.comments.entries()){
      const comment=await this.api('GET',`repos/${this.repo}/issues/comments/${id}`),doc=unpack(comment.body);
      const issuePath=new URL(comment.issue_url).pathname.toLowerCase();require(issuePath.endsWith(`/repos/${this.repo}/issues/${ref.issueNumber}`.toLowerCase()),'Comment belongs to another Issue');
      require(doc.format===FORMAT&&doc.workspace===this.workspace&&doc.key===ref.key&&doc.part===part&&doc.total===ref.comments.length&&typeof doc.data==='string'&&typeof doc.generation==='string','Invalid document chunk');
      generation??=doc.generation;require(generation===doc.generation,'Mixed source document generations');data+=doc.data;
    }
    const result=JSON.parse(data);require(digest(result)===ref.digest,'Source document digest mismatch');return result;
  }
  async load(){
    const issue=await this.indexIssue();if(!issue)return {state:empty(),initialized:false};
    const index=unpack(issue.body);if(index.manifest===null){require(index.revision===0,'Invalid empty index');return {state:empty(),initialized:true};}
    const manifest=await this.readDocument(index.manifest);require(manifest.revision===index.revision,'Index revision mismatch');
    const {testConclusions:conclusionRef,...archiveManifest}=manifest;const state={...archiveManifest,plans:[],rounds:[],annotations:[]};
    for(const plan of manifest.plans){const cases=[];for(const ref of plan.cases)cases.push(await this.readDocument(ref));state.plans.push({...plan,cases});}
    for(const ref of manifest.rounds)state.rounds.push(await this.readDocument(ref));
    for(const ref of manifest.annotations??[])state.annotations.push(await this.readDocument(ref));
    validate(state);require(canonical(await this.readDocument(conclusionRef))===canonical(testConclusions(state)),'Test conclusion does not match records');return {state,initialized:true,manifest};
  }
  async read(){const loaded=await this.load();return {state:loaded.state,info:{mode:'github-issues',repository:`${this.hostname}/${this.repo}`,workspace:this.workspace,actor:this.actor,initialized:loaded.initialized,issue:this.index??null,url:this.index?`https://${this.hostname}/${this.repo}/issues/${this.index}`:null,persistence:loaded.initialized?'github-issues':'not-initialized'}};}
  async initialize(){await this.preflight();if(await this.indexIssue())return this.read();const issue=await this.api('POST',`repos/${this.repo}/issues`,{title:`Testflow · ${this.workspace}`,body:packet({format:FORMAT,workspace:this.workspace,kind:'index',revision:0,manifest:null})});require(number(issue.number)&&issue.user?.login===this.actor,'Index creation uncertain; inspect before retrying');this.index=issue.number;return this.read();}
  async write(expected,candidate){
    await this.preflight();const old=await this.load(),next=proposed(old.state,expected,candidate);require(old.initialized,'请先初始化 GitHub Issues 数据源');if(next===old.state)return this.read();
    this.inventory=await this.issues();
    const manifest={...next,plans:[],rounds:[],annotations:[]};
    for(const plan of next.plans){const cases=[];for(const item of plan.cases){const key=JSON.stringify(['case',plan.id,item.id]);const previous=old.manifest?.plans.find(p=>p.id===plan.id)?.cases.find(ref=>ref.key===key);const issue=previous?{number:previous.issueNumber}:await this.#entity(key,`Testflow 用例 · ${item.id} · ${item.title}`);cases.push(await this.#document(issue.number,key,item,previous));}manifest.plans.push({...plan,cases});}
    for(const round of next.rounds){const key=JSON.stringify(['round',round.id]);const previous=old.manifest?.rounds.find(ref=>ref.key===key);const issue=previous?{number:previous.issueNumber}:await this.#entity(key,`Testflow 轮次 · ${round.name}`);manifest.rounds.push(await this.#document(issue.number,key,round,previous));}
    for(const note of next.annotations??[]){const key=JSON.stringify(['annotation',note.id]);const previous=old.manifest?.annotations.find(ref=>ref.key===key);manifest.annotations.push(await this.#document(this.index,key,note,previous));}
    manifest.testConclusions=await this.#document(this.index,'conclusions',testConclusions(next));
    const ref=await this.#document(this.index,'manifest',manifest),body=packet({format:FORMAT,workspace:this.workspace,kind:'index',revision:next.revision,manifest:ref});
    // The index is the publication point. Earlier incomplete documents remain unreferenced.
    try{await this.api('PATCH',`repos/${this.repo}/issues/${this.index}`,{body});}catch(error){const issue=await this.indexIssue();if(issue.body!==body)throw error;}
    const saved=await this.read();require(canonical(saved.state)===canonical(next),'GitHub save could not be confirmed; inspect source before retrying');return saved;
  }
}
const uuidPattern=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
export class FileSource{
  constructor({repoRoot=process.cwd(),dataDir='testing/testflow',workspace='default',run=command,beforePublish=async()=>{}}){
    require(typeof dataDir==='string'&&!path.isAbsolute(dataDir)&&dataDir.split(/[\\/]/).every(p=>p&&p!=='.'&&p!=='..'&&p.toLowerCase()!=='.git'),'数据目录必须是仓库内的相对目录，不能指向 .git 或仓库根');
    require(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(workspace),'Invalid workspace name');Object.assign(this,{repoRoot:path.resolve(repoRoot),dataDir,workspace,run,beforePublish});
  }
  async git(args){return (await this.run('git',['-C',this.repoRoot,...args])).trim();}
  async setup(){const real=await fs.realpath(this.repoRoot);const top=await this.git(['rev-parse','--show-toplevel']);require(await fs.realpath(top)===real,'--repo-root 必须是实际仓库根目录');this.repoRoot=real;this.root=path.join(real,this.dataDir);await this.safe(this.root);}
  async safe(target){require(target.startsWith(this.repoRoot+path.sep)&&target!==this.repoRoot,'Path escapes repository');let current=this.repoRoot;for(const part of path.relative(this.repoRoot,target).split(path.sep)){current=path.join(current,part);try{const info=await fs.lstat(current);require((await fs.readdir(path.dirname(current))).includes(part),'Use the exact filesystem path spelling; case-only aliases are rejected');require(!info.isSymbolicLink(),'拒绝读写符号链接数据路径');if(current!==target)require(info.isDirectory(),'Parent is not a directory');}catch(error){if(error.code!=='ENOENT')throw error;}}}
  async json(file){await this.safe(file);return JSON.parse(await fs.readFile(file,'utf8'));}
  async owned(){await this.setup();const file=path.join(this.root,'owner.json');try{const owner=await this.json(file);require(owner.format===FORMAT&&owner.workspace===this.workspace,'数据目录属于其他工作台');return true;}catch(error){if(error.code!=='ENOENT')throw error;let names;try{names=await fs.readdir(this.root);}catch(e){if(e.code!=='ENOENT')throw e;names=[];}require(names.length===0,'数据目录已有其他内容，请选择空目录');return false;}}
  async load(){
    if(!await this.owned())return {state:empty(),initialized:false};
    let pointer;try{pointer=await this.json(path.join(this.root,'workspace.json'));}catch(error){if(error.code!=='ENOENT')throw error;return {state:empty(),initialized:false};}
    require(pointer.format===FORMAT&&uuidPattern.test(pointer.generation),'Invalid file generation');const dir=path.join(this.root,'snapshots',pointer.generation);
    const state=await this.generationState(dir);require(digest(state)===pointer.digest,'File snapshot digest mismatch');return {state,initialized:true,generation:pointer.generation};
  }
  async generationState(dir){const definitions=await this.json(path.join(dir,'definitions.json')),rounds=await this.json(path.join(dir,'records.json')),annotations=await this.json(path.join(dir,'annotations.json'));
    const state={...definitions,rounds,annotations};validate(state);require(canonical(await this.json(path.join(dir,'conclusions.json')))===canonical(testConclusions(state)),'Test conclusion does not match records');return state;
  }

  async read(){const loaded=await this.load();const currentFiles=loaded.initialized?['owner.json','workspace.json',...['definitions.json','records.json','annotations.json','conclusions.json'].map(f=>path.join('snapshots',loaded.generation,f))].map(f=>path.join(this.dataDir,f)):[];
    const tracked=loaded.initialized?(await this.git(['ls-files','--',...currentFiles])).split('\n').filter(Boolean):[];
    const dirty=Boolean(await this.git(['status','--porcelain','--untracked-files=all','--',...['owner.json','workspace.json','snapshots'].map(f=>path.join(this.dataDir,f))]))||loaded.initialized&&tracked.length!==currentFiles.length;
    return {state:loaded.state,info:{mode:'repository-files',repository:this.repoRoot,path:this.dataDir,workspace:this.workspace,initialized:loaded.initialized,persistence:loaded.initialized?'working-tree':'not-initialized',head:await this.git(['rev-parse','HEAD']),branch:await this.git(['branch','--show-current']),dirty}};}

  async #publish(state){
    validate(state);await this.owned();const id=randomUUID(),dir=path.join(this.root,'snapshots',id);await this.safe(dir);await fs.mkdir(dir,{recursive:true});
    const {rounds,annotations=[],...definitions}=state;
    for(const [name,value] of [['definitions.json',definitions],['records.json',rounds],['annotations.json',annotations],['conclusions.json',testConclusions(state)]]){const file=path.join(dir,name);await this.safe(file);await fs.writeFile(file,JSON.stringify(value,null,2)+'\n',{flag:'wx',mode:0o600});}
    await this.beforePublish();require(canonical(await this.generationState(dir))===canonical(state),'Staged generation read-back mismatch');
    const pointer={format:FORMAT,generation:id,digest:digest(state)},pending=path.join(this.root,`workspace-${id}.tmp`);await this.safe(pending);await fs.writeFile(pending,JSON.stringify(pointer)+'\n',{flag:'wx',mode:0o600});
    await this.safe(path.join(this.root,'workspace.json'));await fs.rename(pending,path.join(this.root,'workspace.json'));
  }
  async initialize(){if(await this.owned()){const old=await this.load();if(old.initialized)return this.read();}else{await this.safe(path.join(this.root,'owner.json'));await fs.mkdir(this.root,{recursive:true});await fs.writeFile(path.join(this.root,'owner.json'),JSON.stringify({format:FORMAT,workspace:this.workspace})+'\n',{flag:'wx',mode:0o600});}await this.#publish(empty());return this.read();}
  async write(expected,candidate){const old=await this.load(),next=proposed(old.state,expected,candidate);require(old.initialized,'请先初始化仓库文件数据源');if(next!==old.state)await this.#publish(next);const saved=await this.read();require(canonical(saved.state)===canonical(next),'File save could not be confirmed');return saved;}
  async commit(expected){
    const old=await this.load();require(old.initialized&&old.state.revision===expected,'请刷新并核对测试数据后再提交');require(await this.git(['branch','--show-current']),'Detached HEAD: cannot commit test data');require(await this.git(['config','user.name']),'Git user.name required');require(await this.git(['config','user.email']),'Git user.email required');
    const files=['owner.json','workspace.json'];
    const snapshots=path.join(this.root,'snapshots');await this.safe(snapshots);
    for(const generation of await fs.readdir(snapshots)){require(uuidPattern.test(generation),'Unexpected snapshot path');const dir=path.join(snapshots,generation);await this.safe(dir);const names=await fs.readdir(dir);require(names.length===4&&names.every(n=>['definitions.json','records.json','annotations.json','conclusions.json'].includes(n)),'Incomplete snapshot; preserve pending files and inspect before committing');await this.generationState(dir);for(const name of names){const file=path.join(dir,name);await this.safe(file);require((await fs.lstat(file)).isFile(),'Non-regular data file');files.push(path.relative(this.root,file));}}
    const paths=files.map(f=>path.join(this.dataDir,f));for(const file of paths)await this.safe(path.join(this.repoRoot,file));
    if(!await this.git(['status','--porcelain','--',...paths])&&(await this.git(['ls-files','--',...paths])).split('\n').filter(Boolean).length===paths.length)return this.read();
    await this.git(['add','--',...paths]);await this.git(['commit','--only','-m',`Record Testflow ${this.workspace} revision ${old.state.revision}`,'--',...paths]);
    const saved=await this.read();require(!saved.info.dirty,'Commit finished but test files changed again; inspect working tree');saved.info.persistence='committed';return saved;
  }
}
