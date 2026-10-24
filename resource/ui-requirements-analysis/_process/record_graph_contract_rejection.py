"""Record the user's rejection of the last graph semantics; withdraw final-review readiness."""
import sys,json
from pathlib import Path
w=Path(__file__).resolve().parent
sys.path.insert(0,str(w.parent.parent.parent/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
m=wf.read(w/'analysis-model.json')
e=w/'evidence/user-graph-contract-review.md'
e.write_text('用户本轮原文：\n\n有向边呢？ 状态迁移图没有边？？？\n规范要求的需求是什么？ 需求是从状态图转换？为什么只有一个需求？\n\nF:\\CX_notes\\cx-learn-notes\\android-plan-checkin\\plans\\history\\requirements-analysis-project-test\\review.html\n\n查看参考设计\n\n处理：这是对当前分析建模和交付语义的校核，不是最终验收同意，也不自动引入参考案例的历史业务范围。\n',encoding='utf-8')
sid='HUMAN-GRAPH-REVIEW'
m['sources']=[s for s in m['sources'] if s['id']!=sid]+[{'id':sid,'kind':'human','uri':'conversation:current-user-review',
    'locator':'当前用户完整校核及参考HTML路径','readRanges':['当前用户消息全文'],'evidencePath':'_process/evidence/user-graph-contract-review.md','sha256':wf.file_hash(e)}]
m['phase']='incomplete'
m['rounds'].append({'id':'REVIEW-GRAPH-CONVERSION','kind':'build','nodeIds':[s['id'] for s in m['states']],
    'checks':[],'changes':[{'kind':'update','entityId':'UI-001','meaning':'用户要求按状态迁移推导原子需求；当前画板观察清单及单一总需求不能作为该双图流程的完成结果，待重建分析关系。','sourceIds':[sid]}],
    'openFrontier':['F-UI','UI-001']})
wf.write(w/'analysis-model.json',m)
state=wf.read(w/'run-state.json')
state.update(waiting_for_user=False,pause_reason=None,active_node_id=None,
    next_action='按参考核对通用状态迁移→原子需求→需求图合同，区分PRD总功能与分析原子需求；重建有来源的UI状态迁移，保留未能确定的关系，不引入历史业务实现要求。当前结果不可提交最终确认。')
wf.write(w/'run-state.json',state)
wf.save_current(w.parent)
result=wf.gate(w.parent,w.parent,w/'model-review.json')
(w/'evidence/reference-contract-review.md').write_text('''# 参考对照的实际发现

- 用户指定参考：plans/history/requirements-analysis-project-test/review.html，已在浏览器实际查看状态、迁移需求详情与需求覆盖图。
- 参考模型：66状态、525迁移、525原子需求。需求图：525节点、750条路线实际使用的有向衔接。
- 参考链条：PRD功能点 → 状态及事件/条件迁移 → 每迁移一条原子需求 → 按终态等于初态派生候选衔接 → 连续覆盖路线投影。
- 实际打开示例：固定星期新建草案 → 选择每周目标类型（有条件）→ 每周N天新建草案；对应一条原子需求，含前提、操作、明确结果、UI与来源。
- 当前产物：23画板观察目标、0迁移、1项总视觉约束，没有完成上述转换。上一轮“等待整体验收”结论撤回，当前工作阶段为 incomplete。
- 原因：将PRD总需求UI-001的数量与分析原子需求数量混同；把状态约束扩展当作替代状态迁移分析的完成通道。程序与独立评审通过的是被改后的合同，不能证明满足用户要求的图语义。
- 范围依据仍是当前UI PRD。参考的读取、保存、存储、统计、权限、日期算法等业务要求不能复制成本次需求；当前PRD的视觉范围不变。
- 本记录是方法校核，不将工具/模型缺陷转嫁为PRD业务歧义，不要求用户补充范围外业务实现。
''',encoding='utf-8')
print(json.dumps({'phase':m['phase'],'gate_status':result['gate_status'],'ready_for_final_confirmation':False,'pendingNodes':len(wf.read(w/'run-state.json')['pending_node_ids'])},ensure_ascii=False))

