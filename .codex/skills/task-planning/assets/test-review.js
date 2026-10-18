// Extend the verified upstream review. Preserve its data, layout, and Canvas interactions.
const TP=JSON.parse(document.getElementById('test-data').textContent),P=TP.plan,G=TP.gate;
const primaryTests=new Map(P.cases.filter(c=>c.kind==='primary').map(c=>[c.requirementId,c]));
const testById=new Map(P.cases.map(c=>[c.id,c]));
const testStatus={pending:'待验收',failed:'验收失败',passed:'验收通过'};
const testColor={pending:'#62758e',failed:'#b62e31',passed:'#23784e'};
let testMode=false;
const originalGraph=graph,originalDraw=draw,originalSwitchMode=switchMode;
const originalSelectRequirement=selectRequirement,originalContinuationDetail=continuationDetail;
const originalCoverageDetail=coverageDetail,originalEdgeText=edgeText;
// Only the view IDs are translated back to requirement IDs so the source layout stays identical.
const mappedTestNodes=P.testGraph.nodes.map(n=>({...n,id:n.requirementId}));
const mappedTestEdges=P.testGraph.edges.map(e=>({...e,id:e.sourceEdgeId,
    from:testById.get(e.from).requirementId,to:testById.get(e.to).requirementId}));
graph=function(){return testMode?{nodes:mappedTestNodes,edges:mappedTestEdges,
    starts:P.testGraph.entryCaseIds.map(id=>testById.get(id).requirementId),positions:layouts.requirement}:originalGraph();};
draw=function(){
    originalDraw();if(!testMode)return;
    const v=views[mode];ctx.save();ctx.translate(v.x,v.y);ctx.scale(v.scale,v.scale);
    for(const node of graph().nodes){const pos=position(node.id),c=primaryTests.get(node.id);
        ctx.font='11px system-ui';ctx.textAlign='right';ctx.fillStyle=testColor[c.result.status];
        ctx.fillText(testStatus[c.result.status],pos.x+pos.w-8,pos.y-8);}
    ctx.restore();$('root-legend').textContent='入口测试（对应入口需求）';
    $('graph-caption').textContent='测试图：'+P.testGraph.nodes.length+' 项 · '+P.testGraph.edges.length+' 条有向边 · '+
        P.testGraph.entryStateIds.length+' 个真实流程起点 · '+P.testGraph.entryCaseIds.length+' 个入口测试 · 与需求图结构、位置一致 · '+Math.round(v.scale*100)+'%';
};
switchMode=function(next){testMode=next==='test';originalSwitchMode(testMode?'requirement':next);
    $('test-mode').setAttribute('aria-pressed',String(testMode));
    $('requirement-mode').setAttribute('aria-pressed',String(!testMode&&mode==='requirement'));
    $('coverage-route').textContent=testMode?'继承路线与校验':'覆盖路线与校验';
};
function showTestChain(c,host){
    const section=block('完整链路：从真实起点到当前测试',host);
    const matches=P.routes.routes.filter(r=>(rootChoice==='all'||r.entryStateId===rootChoice)&&r.steps.some(s=>s.caseId===c.id));
    if(!matches.length){el('p','输入需求路线未提供从所选起点到本项的链路；不把本项提升为新起点。',section,'empty');return;}
    const chooser=el('select',undefined,section,'route-select'),body=el('div',undefined,section);
    chooser.setAttribute('aria-label','选择继承需求路线');
    options(chooser,matches.map((r,i)=>({value:String(i),label:'第 '+(r.sourceRouteIndex+1)+' 段 · 从“'+states.get(r.entryStateId).title+'”开始'})),'0');
    function display(){body.replaceChildren();const route=matches[Number(chooser.value)],index=route.steps.findIndex(s=>s.caseId===c.id),steps=route.steps.slice(0,index+1);
        el('p','沿用需求覆盖路线，到本项第一次出现为止，共 '+steps.length+' 步；重复经过保留。',body,'muted');
        const check=route.contextCheck;
        if(!['passed','finite_domain_passed','no_guard_constraints'].includes(check.status))el('p',check.status==='conflict'?'源路线在第 '+check.step+' 步存在条件冲突；下列内容为结构链路，不能直接作为可执行顺序。':'源路线条件尚未验证通过。',body,'condition');
        if(typeof contextConditions==='function')contextConditions(check.initialContext,body);
        const more=el('details',undefined,body);el('summary','展开完整中文链路',more);
        el('p','从“'+states.get(route.entryStateId).title+'”开始。'+steps.map(s=>sentence(transitions.get(s.transitionId))).join(''),more,'narrative');
        const ol=el('ol',undefined,more,'steps');for(const s of steps){const li=el('li',undefined,ol);btn(sentence(transitions.get(s.transitionId)),()=>selectRequirement(testById.get(s.caseId).requirementId),li).className='step-action';}}
    chooser.onchange=display;display();
}
function testDetail(requirementId){
    const c=primaryTests.get(requirementId),t=transitions.get(c.transitionId),target=states.get(c.to);
    const host=setDetail('测试项 · 对应一项原子需求',c.title);
    $('detail-status').textContent=testStatus[c.result.status]+' · '+(c.readiness==='ready'?'测试准备已定义':'测试准备待补充');
    const relation=el('div',undefined,host,'transition-summary');el('div',states.get(c.from).title,relation,'state-label');el('div','→',relation);el('div',target.title,relation,'state-label');
    el('p','执行条件：'+c.guard,host,'condition');
    const setup=block('准备条件',host);list(c.setup,setup);
    const steps=block('测试步骤',host),ol=el('ol',undefined,steps,'steps');for(const step of c.steps)el('li',step,ol);
    const functionality=block('功能预期与预期状态',host);el('p','预期状态：'+c.expectedState,functionality);list(c.assertions.filter(a=>a.kind==='functional').map(a=>a.text),functionality);
    const visualExpectation=block('视觉预期',host);list(c.assertions.filter(a=>a.kind==='visual').map(a=>a.text),visualExpectation);
    visual([...(c.uiRefs||[]),...(target.uiRefs||[])],target.facts.filter(isVisual),[...t.sourceIds,...target.sourceIds],host);
    const evidence=block('验收结论与证据',host);el('p','当前结论：'+testStatus[c.result.status],evidence);
    if(c.result.staleEvidence)el('p','旧证据已失效：'+c.result.staleEvidence.reason,evidence,'condition');
    const observations=c.result.observations||[];
    if(!observations.length)el('p','尚未执行；实际结果、功能证据和视觉截图待采集。',evidence,'muted');
    for(const instance of c.instances){const group=block('验收实例：'+(instance.label||instance.environment||'标准场景'),evidence);
        for(const a of c.assertions.filter(x=>x.applicability==='supported')){const observation=observations.find(o=>o.instanceId===instance.id&&o.assertionId===a.id);
            const row=el('div',undefined,group,'assertion');el('p','预期：'+a.text,row);el('p','结论：'+(observation?testStatus[observation.verdict]:'待验收'),row);el('p','实际：'+(observation?.actual||'待记录'),row);
            if(observation?.evidence?.length){for(const ev of observation.evidence){el('p','证据：'+ev.path+' · '+ev.locator,row,'source');if(/\.(png|jpe?g|webp)$/i.test(ev.path)&&!ev.path.includes('..')&&!/[:\\]/.test(ev.path)){const img=el('img',undefined,row);img.src=ev.path;img.alt='实测截图';img.style.maxWidth='100%';}}}
            else el('p','证据：待采集',row,'muted');}}
    list(c.evidenceRequirements,evidence);
    showTestChain(c,host);
    if(c.globalConstraintIds.length){const shared=block('共享约束',host);list(P.sharedConstraints.filter(x=>c.globalConstraintIds.includes(x.id)).map(x=>x.text),shared);}
    showSources(t.sourceIds,host);
}
selectRequirement=function(id){if(!testMode)return originalSelectRequirement(id);selected={kind:'requirement',id};testDetail(id);queueDraw();};
continuationDetail=function(id){if(!testMode)return originalContinuationDetail(id);
    const edge=mappedTestEdges.find(e=>e.id===id),a=primaryTests.get(edge.from),b=primaryTests.get(edge.to);
    const host=setDetail('测试项之间的衔接','完成前项后，按条件执行后项');
    el('p','此边原样继承需求图，同一连接只画一次；路线重复使用次数单独记录。',host,'narrative');
    el('h4','前项测试',host);btn(a.title,()=>selectRequirement(a.requirementId),host);
    el('p','衔接状态：'+states.get(a.to).title,host,'condition');
    el('h4','后项测试',host);btn(b.title,()=>selectRequirement(b.requirementId),host);
    el('p','后项操作：'+b.steps.join('；'),host);el('p','后项条件：'+b.guard,host,'condition');
    el('p','源路线经过此边 '+(edge.usageCount||0)+' 次。'+coverageStatus(),host,'muted');
    const routes=block('所属需求路线',host);for(const r of P.routes.routes){const positions=[];for(let i=1;i<r.steps.length;i++)if(r.steps[i-1].caseId===a.id&&r.steps[i].caseId===b.id)positions.push(i+1);if(positions.length)el('p','第 '+(r.sourceRouteIndex+1)+' 段：后项位于第 '+positions.join('、')+' 步。',routes);}
};
edgeText=function(edge){return testMode?primaryTests.get(edge.from).title+'\n→ '+primaryTests.get(edge.to).title+'\n继承需求连接，仅画一次；源路线使用 '+(edge.usageCount||0)+' 次':originalEdgeText(edge);};
coverageDetail=function(){originalCoverageDetail();if(testMode){$('detail-kind').textContent='继承的需求路线';$('detail-title').textContent='测试顺序沿用需求路线';el('p','本轮只建立需求到测试的映射，没有重新计算路线。可执行条件、访问次数和最优性结论均沿用上游；未证明最短时不改写为最短。实际数据准备和产品验收另行完成。',$('detail-body'),'condition');}};
$('test-mode').onclick=()=>switchMode('test');$('coverage-route').onclick=coverageDetail;
$('summary').textContent=P.testGraph.nodes.length+' 项主测试 · '+G.acceptance.pending+' 待验收 · '+G.acceptance.failed+' 失败 · '+G.acceptance.passed+' 通过 · '+(P.regressionPolicy.mode==='deferred'?'本轮不纳入回归':'回归另列，不改主图');
switchMode('test');
