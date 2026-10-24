# 总门禁：复用证据与补全验收

## 验收目标

| 检查项 | 通过条件 | 证据 |
| --- | --- | --- |
| F-STAGES | 第一步、第二步、第三步当前检查均通过 | 各步重查结果；复用匹配摘要的独立报告 |
| F-CONSISTENCY | 当前状态摘要、需求绑定、HTML 展示数据和交付文件一致 | 程序重算及文件摘要 |

运行 `python SKILL_DIR/scripts/analyze.py final RUN`，输出 `gate-result.json`。总门禁复用有效评审，补查跨步骤一致性与缺项，不新增完整语义评审或最终人工批准。

## 证据复用与失效

| 内容变化 | 重查范围 |
| --- | --- |
| 来源含义、范围、澄清答案、状态、迁移、条件 | 第一步及其全部下游；核对来源实际版本 |
| 原子需求、验收、重启政策、需求图 | 第二步及 HTML；第一步输入未变则复用其语义报告 |
| HTML 模板、布局或展示适配器 | 第三步及跨步骤一致性；状态与需求语义报告仍可复用 |
| 仅中间笔记、日志或缓存位置 | 不改变检查输入和证据有效性时，不触发无关重评 |

机械检查重跑，不能直接采用历史 passed。语义报告匹配当前 inputDigest 和 contractDigest 后复用；规则或相关检查实现改变则失效。可读取的本地来源、预览和澄清文档纳入输入摘要；远程资料变化须重新读取并更新来源摘要／版本。相对路径相对 RUN。

## 独立语义报告

初始化时通过 `--analyzer-context` 登记实际分析会话／代理引用，工具默认保存到 `_process/analysis-context.json`。分析上下文确实变化时更新该参数并核对评审有效性，不生成随机引用代替真实会话。初始报告保持 pending。

独立上下文读取相关 reference、完整阶段产物、全部原始来源和澄清记录，完成逐对象评审。第一步核对状态四项准入、迁移独立性、逐条自环、守卫／事实／效果一致性与双向来源覆盖；第二步核对每项需求的原子性、适用性和验收断言。发现缺项先修复，再评审当前内容。

报告合同如下；示例只示意一个对象，实际集合按阶段检查结果的 reviewTargets 全量填写。

```json
{
  "stage": "state",
  "inputDigest": "当前步骤输入摘要",
  "contractDigest": "当前步骤规则摘要",
  "analyzerContext": "已登记的实际分析上下文",
  "reviewer": {"independent": true, "context": "另一实际评审上下文"},
  "sourceIds": ["SRC1"],
  "objects": [
    {"id": "S1", "status": "pending", "reason": "", "evidence": []}
  ],
  "closure": {"openItems": [], "reason": ""},
  "criteria": [
    {"id": "S-MEANING", "status": "pending", "reason": "", "evidence": []},
    {"id": "S-COVERAGE", "status": "pending", "reason": "", "evidence": []}
  ],
  "findings": []
}
```

- `analyzerContext` 匹配运行记录，评审者 context 非空且不同；执行者依据真实会话核对身份。
- `sourceIds` 恰为当前全部来源。每项 evidence 为 `{"sourceId":"SRC1","locator":"具体条款／画板区域"}`，不得只写不可解析的证据字符串。
- 第一步 objects 恰覆盖全部状态和迁移；第二步恰覆盖全部原子需求，不漏项、不重复、不混入旧对象。每个对象有状态、具体判断和来源定位；一个总体“通过”不能代替逐对象结论。
- criteria 恰为 S-MEANING／S-COVERAGE 或 R-ATOMIC／R-ACCEPTANCE。每项均有判断与定位，不以重述规范或统计数量作为证据。
- closure 说明最后变更后完成了哪些全量复核，openItems 保存仍待分析的具体对象／义务。存在未分析项、未解决问题或开放 findings 时不能闭合；不要求固定轮次、十维日志或另建收敛报告。

程序检查摘要、上下文区别、对象与来源集合、定位结构和结论；不能证明引用真实、定位内容支持结论或评审者实际独立。执行者仍须核对实际会话及原文。输入截断、来源不可读、缺独立上下文或证据不足时保持 pending；发现实质问题则 failed 并定位修复方向。

## 结果与交付

- passed：必需项均有当前有效证据，无开放问题、未分析项或失败。
- failed：已知条件不满足；指出对象、原因和修复起点。
- pending：缺输入、缺评审、证据失效或搜索未完成。

完整可行覆盖可以保留 not_proven 并通过，不能称为最短。HTML 静态通过不代表浏览器真实验收或产品运行验收。

默认交付状态 JSON、需求 JSON、只读 HTML 和总门禁 JSON；发生人工澄清时保留可访问的确认文档。中间证据放在 _process，不固定日志、快照、目录树或额外 manifest。
