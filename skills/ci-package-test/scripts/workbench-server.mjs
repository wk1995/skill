#!/usr/bin/env node
import http from 'node:http';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomBytes} from 'node:crypto';
import {GitHubSource,FileSource,require} from './workspace-sources.mjs';
const assets=fileURLToPath(new URL('../assets/workbench/',import.meta.url));
export function options(args){const result={mode:'github-issues',port:4317};const fields={'--mode':'mode','--repo':'repo','--hostname':'hostname','--workspace':'workspace','--issue':'issue','--repo-root':'repoRoot','--data-dir':'dataDir','--port':'port'};
  for(let i=0;i<args.length;i++){const field=Object.hasOwn(fields,args[i])?fields[args[i]]:null;require(field&&args[i+1]&&!args[i+1].startsWith('--'),`Unknown or missing option: ${args[i]}`);result[field]=args[++i];}
  require(['github-issues','repository-files'].includes(result.mode),'Unsupported data-source mode');for(const key of ['port','issue'])if(result[key]!==undefined){require(/^\d+$/.test(String(result[key])),`Invalid ${key}`);result[key]=Number(result[key]);}require(result.port>=0&&result.port<=65535,'Invalid port');return result;
}
export async function createWorkbenchServer({source,port=0}){
  const session=randomBytes(32).toString('hex');let base;let queue=Promise.resolve();
  const send=(res,status,value)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(value));};
  const server=http.createServer(async(req,res)=>{
    try{
      require(req.headers.host===new URL(base).host,'Unexpected Host');
      require(!req.headers.origin||req.headers.origin===base,'Cross-origin request rejected');
      require(!req.headers['sec-fetch-site']||['same-origin','none'].includes(req.headers['sec-fetch-site']),'Cross-site request rejected');
      const url=new URL(req.url,base);
      if(url.pathname==='/api/config'&&req.method==='GET')return send(res,200,{session,mode:source instanceof FileSource?'repository-files':'github-issues'});
      if(url.pathname==='/api/workspace'&&req.method==='GET')return send(res,200,await source.read());
      if(['/api/workspace','/api/initialize','/api/commit'].includes(url.pathname)&&['POST','PUT'].includes(req.method)){
        require(req.method===(url.pathname==='/api/workspace'?'PUT':'POST'),'Unsupported method');
        require(req.headers['x-testflow-session']===session,'Missing session token');require(req.headers['content-type']?.split(';')[0]==='application/json','JSON content type required');
        const chunks=[];let bytes=0;for await(const data of req){bytes+=data.length;require(bytes<=16*1024*1024,'Request too large');chunks.push(data);}
        const input=JSON.parse(Buffer.concat(chunks).toString('utf8'));require(input&&typeof input==='object'&&!Array.isArray(input),'Object body required');
        // Serialize this service's writes; this is not a distributed lock.
        const task=queue.then(async()=>{
          if(url.pathname==='/api/workspace')return source.write(input.expectedRevision,input.state);
          if(url.pathname==='/api/initialize'){require(Object.keys(input).length===0,'Initialize takes no replacement data');return source.initialize();}
          require(source instanceof FileSource,'Git commit is only available in file mode');return source.commit(input.expectedRevision);
        });queue=task.catch(()=>{});return send(res,200,await task);
      }
      if(url.pathname.startsWith('/api/'))return send(res,404,{error:'Unknown endpoint or method'});
      require(req.method==='GET'||req.method==='HEAD','Unsupported method');
      const name=url.pathname==='/'?'index.html':url.pathname.slice(1);require(/^(?:index\.html|styles\.css|[a-z-]+\.mjs)$/.test(name),'Unknown static asset');
      const file=path.join(assets,name);const data=await fs.readFile(file);res.writeHead(200,{'Content-Type':name.endsWith('.mjs')?'text/javascript; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"});res.end(req.method==='HEAD'?undefined:data);
    }catch(error){if(!res.headersSent)send(res,error.code==='ENOENT'?404:400,{error:error.message});else res.end();}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});base=`http://127.0.0.1:${server.address().port}`;
  return {server,url:base,close:()=>new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()))};
}
export async function main(args=process.argv.slice(2)){
  if(args.includes('--help')){console.log('node scripts/workbench-server.mjs --repo OWNER/REPO [--mode github-issues] [--issue NUMBER] [--hostname HOST] [--workspace NAME] [--port 4317]\nnode scripts/workbench-server.mjs --mode repository-files --repo-root /absolute/repository --data-dir testing/testflow [--workspace NAME] [--port 4317]');return;}
  const config=options(args),source=config.mode==='repository-files'?new FileSource(config):new GitHubSource(config);
  if(source instanceof GitHubSource)await source.preflight();else await source.setup();
  const {url}=await createWorkbenchServer({source,port:config.port});console.log(`Testflow ${url}\n数据源: ${config.mode} · ${config.repo??source.repoRoot}\n只监听本机；网页初始化后才能保存。文件保存与 Git 提交分开。`);
}
if(process.argv[1]&&await fs.realpath(process.argv[1]).catch(()=>null)===fileURLToPath(import.meta.url))main().catch(error=>{console.error(error.message);process.exitCode=1;});
