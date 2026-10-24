// Links are references only: no Issue reads, writes, attachments or status synchronization.
export function issueURL(value) {
  if (typeof value !== 'string') throw new Error('Issue URL required');
  let url;try { url=new URL(value.trim()); } catch { throw new Error('Invalid Issue URL'); }
  if(url.protocol!=='https:'||url.username||url.password||url.port||url.search||!/^\/[^/]+\/[^/]+\/issues\/[1-9]\d*\/?$/.test(url.pathname)||/%|\\/.test(url.pathname))throw new Error('Use an HTTPS GitHub Issue URL: https://HOST/OWNER/REPO/issues/NUMBER');
  url.hash='';url.pathname=url.pathname.replace(/\/$/,'');return url.href;
}
export const parseIssueURLs=value=>[...new Set(value.split(/\r?\n/).map(line=>line.trim()).filter(Boolean).map(issueURL))];
export const recordIssues=(round,observationId)=>[...new Set((round.issueLinks??[]).filter(link=>link.observationId===observationId).map(link=>link.url))];
export function validateIssueLinks(round) {
  if(round.issueLinks===undefined)return;
  if(!Array.isArray(round.issueLinks))throw new Error('issueLinks: array required');
  const ids=new Set();
  for(const link of round.issueLinks){
    if(!link||typeof link!=='object'||Array.isArray(link)||!['id','observationId','actor'].every(key=>typeof link[key]==='string'&&link[key].trim())||ids.has(link.id))throw new Error('Invalid/duplicate Issue association');
    ids.add(link.id);
    if(!round.observations.some(item=>item.id===link.observationId))throw new Error('Issue observation not found in this round');
    if(issueURL(link.url)!==link.url)throw new Error('Issue URL must be canonical');
    if(typeof link.createdAt!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(link.createdAt)||!Number.isFinite(Date.parse(link.createdAt))||new Date(`${link.createdAt.slice(0,10)}T00:00:00Z`).toISOString().slice(0,10)!==link.createdAt.slice(0,10))throw new Error('Issue association timestamp with timezone required');
  }
}
