import assert from 'node:assert/strict';
import {GitHubSource} from '../scripts/workspace-sources.mjs';
export class FakeGitHub{
 constructor(){this.items=new Map();this.comments=new Map();this.actor='tester';this.calls=[];this.next=1;this.commentId=10;this.fail=null;}
 async api(method,route,data){this.calls.push({method,route,data});if(this.fail?.(method,route,data)==='before')throw new Error('injected network failure');let result;
  if(route==='user')result={login:this.actor};else if(route==='repos/owner/repo')result={full_name:'owner/repo',has_issues:true};
  else if(method==='GET'&&route.includes('?'))result=[...this.items.values()];
  else if(method==='POST'&&route.endsWith('/issues')){result={number:this.next++,user:{login:this.actor},...data};this.items.set(result.number,result);}
  else if(route.includes('/issues/comments/'))result=this.comments.get(Number(route.split('/').at(-1)));
  else if(method==='POST'&&route.endsWith('/comments')){const issue=Number(route.split('/').at(-2));result={id:this.commentId++,user:{login:this.actor},issue_url:`https://api.github.com/repos/owner/repo/issues/${issue}`,...data};this.comments.set(result.id,result);}
  else{const id=Number(route.split('/').at(-1));result=this.items.get(id);if(method==='PATCH')Object.assign(result,data);}
  if(this.fail?.(method,route,data)==='after')throw new Error('injected uncertain outcome');assert(result,'Unknown fake API route: '+route);return structuredClone(result);
 }
 source(){const s=new GitHubSource({repo:'owner/repo'});s.api=this.api.bind(this);return s;}
 writes(){return this.calls.filter(c=>c.method!=='GET').length;}
}
