export const TEST_LOCATION={field:'case.testLocation',optional:true,required:['screen'],strategies:['resource-id','accessibility-id','text','test-id','css','xpath'],verification:'Declared navigation/locator hints only. Confirm the live screen and matching control before operating; never infer a pass or use guessed coordinates.'};
const require=(ok,message)=>{if(!ok)throw new Error(message);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&value.trim().length>0;
export function validateTestLocation(item) {
  if(item.testLocation===undefined)return;
  const hint=item.testLocation;
  require(object(hint)&&text(hint.screen),'testLocation: screen text required');
  require(Object.keys(hint).every(key=>['app','screen','entryPath','targets','verify'].includes(key)),'testLocation: unsupported field');
  for(const key of ['app','verify'])if(Object.hasOwn(hint,key))require(text(hint[key]),`testLocation.${key}: text required`);
  if(Object.hasOwn(hint,'entryPath'))require(Array.isArray(hint.entryPath)&&hint.entryPath.every(text),'testLocation.entryPath: text array required');
  if(Object.hasOwn(hint,'targets')) {
    require(Array.isArray(hint.targets),'testLocation.targets: array required');
    for(const target of hint.targets) {
      require(object(target)&&['name','by','value','action'].every(key=>text(target[key])),'testLocation target: name/by/value/action required');
      require(Object.keys(target).length===4&&TEST_LOCATION.strategies.includes(target.by),'testLocation target: unsupported locator strategy or field');
    }
  }
}
export function locationHint(item) {
  validateTestLocation(item);
  return {available:item.testLocation!==undefined,verification:'unverified-live-screen',...(item.testLocation?structuredClone(item.testLocation):{}),requirement:TEST_LOCATION.verification};
}
export function formatTestLocation(item,context) {
  const hint=locationHint(item);
  return [
    `测试定位提示（计划信息，未核对当前设备界面）`,
    `版本 / 源码：${context.version} / ${context.source}`,
    `CI / 产物：${context.build||'未提供'}`,
    `方案 / 轮次 / 环境：${context.planId} / ${context.roundId||'方案定义'} / ${context.environmentId||'未选择环境'}`,
    ...(context.environment?[`设备 / 配置：${context.environment.label} / ${context.environment.kind} / ${context.environment.configuration}`]:[]),
    `用例：${item.id} · ${item.title}`,
    `状态：${context.state??'定义'}；前置依赖：${(item.dependsOn??[]).join(', ')||'无'}`,
    ...(context.unresolvedFailureId?[`仍有未解决失败：${context.unresolvedFailureId}`]:[]),
    ...(context.dependencyStale?['前置证据已变化，旧结果需要重新验证。']:[]),
    ...(context.unmetDependencies?.length?[`未满足前置：${context.unmetDependencies.map(dep=>`${dep.caseId} (${dep.state})`).join(', ')}`]:[]),
    hint.available?`应用：${hint.app??'未提供'}\n页面：${hint.screen}`:'尚未配置页面 / 控件定位，先核对实际界面。',
    ...(hint.entryPath??[]).map((step,index)=>`入口 ${index+1}：${step}`),
    ...(hint.targets??[]).map(target=>`${target.name} [${target.by}=${target.value}]：${target.action}`),
    `操作前核对：${hint.verify??'确认当前页面、目标控件和所选设备/环境；定位不匹配时先刷新截图或界面树。'}`,
    `前置条件：${item.preconditions}\n步骤：${item.steps}\n预期：${item.expected}`,
    '这些提示不证明已到达页面或测试通过。使用实际截图/界面树确认控件；不要凭旧坐标点击。'
  ].join('\n');
}
