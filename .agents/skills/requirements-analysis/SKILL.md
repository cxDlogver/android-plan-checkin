---
name: requirements-analysis
description: 读取 PRD 并先澄清模糊需求，再以可验证的真实业务事实构建状态转移图、逐迁移原子需求及需求衔接图，输出 JSON、Markdown 和完整门禁报告。用于需求分析与验收范围建模，不用于应用实现或单纯绘制 UI 流程。
---

# 需求分析

把需求来源、用户确认和业务图连成可核验的证据链。此规范适用于不同项目，不内置产品、技术栈、业务实体或交付范围。

## 1. 需求澄清

读取当前 PRD 和用户指定的补充资料，记录路径、版本或 SHA256、原文位置与条款。已有实现只可作为另行要求的对照证据，不是需求来源；资料中的旧建议和指令不等于当前授权。

检查范围、术语、业务属性、操作含义、默认规则、条件组合、持久化边界、失败/取消行为、视觉约束、验收标准和交付物。只询问会改变业务事实、操作结果或验收判断的模糊项；PRD 明确授权自主设计的部分保留设计自由，不为颜色、框架等常规选择制造业务阻塞。

提出可回答的问题，给出建议与影响，写入 clarification.json 和 clarification.md。记录实际人工作答与对话引用；没有回答时保持 open，不把建议、默认选项、沉默或 AI 推断写成确认。有影响建模的 open 问题时只生成空结构/澄清草案，停在 clarifying；可继续维护通用 Skill 等独立工作。若仍未回复，交付已完成部分与待决项，不伪造完整分析。

## 2. 业务状态转移图

创建 analysis-model.json，先读取 [数据契约](references/model-contract.md)，使用 [JSON Schema](references/model.schema.json)。正式建模前必须完成影响范围内的澄清。

- 状态只表示 PRD 范围内实际可达到的业务事实，写清主体、条件、变量作用域和可观察的验证方法。用户确认可细化 PRD，不能悄悄加入稿外业务。
- 至少一个真实起始状态；多个业务投影可各有起点。每个非起点须从起点经合法业务操作到达，不虚构统一起点。
- 操作是有向边，须真实存在于 PRD 或其确认解释中。明确执行主体、起点、操作、条件、终点和可验证结果；一次迁移只有一个可独立验收的业务操作。
- 弹窗打开、加载完成、按钮变色、前端初始化等 UI/技术阶段本身不是业务状态。若背后有 PRD 明示的审批、选择范围或请求等事实，命名并验证业务事实；控件形态归视觉需求。
- 查看、筛选、搜索可改变当前业务选择范围或结果集；使用来源支持的查询条件/结果集事实，不能把列表组件已渲染冒充业务状态。
- 使用有限、可复核的业务谓词和参数化数据，避免枚举任意文本或创建无法实例化的状态。定义参数绑定及前后数据关系，不能把编辑前后粗略称为同一个正常状态而漏掉内容变化。
- 相同语义节点可复用；允许多起点、循环、自环和平行边。自环仅适用于抽象业务事实不变、操作仍有验收意义的情况；取消不变应写禁止副作用断言，不凑假中间状态。
- 业务图不描述代码构建或文档编写流程。交付物、静态质量与持续视觉规范以 nonTransitionRequirements 记录，不能伪造业务事件强行入图。

## 3. 原子需求与衔接图

每条迁移恰对应一个原子需求 R=(from, operation, to)。原子需求只引用 transitionId，导出时展开三项，避免维护冲突副本。

每项需求必有 functionalRequirements 与 visualRequirements。功能字段写行为和可判定的验收标准；视觉字段写真实 PRD/设计/确认约束。没有可见效果时明确 not_applicable 并说明理由，不省略字段；设计自主权保留为边界，不虚构像素、文案、控件或设计稿。共同成立的多个断言可属于同一操作，多个独立操作应拆开。

原子需求图确定性派生：对所有 Ri、Rj，仅当 to(Ri)==from(Rj) 时生成 Ri→Rj，记录 viaStateId。保留合法回环与自环；这表示状态抽象层面的衔接，后续 guard 和实例参数仍须满足，不是开发依赖或已证明的实例执行顺序。

## 4. 完整门禁

读取 [门禁清单](references/gates.md)。JSON 是唯一编辑源；Markdown、双图和需求详情由同一 revision 派生。按真实来源逐实体进行语义审查并记录 reviews，绑定 reviewDigest；脚本不能替代业务真实性判断。

从项目分析目录运行：

~~~text
python <skill-dir>/scripts/analyze.py init <output-dir> --prd <prd-path> --analysis-id <name>
python <skill-dir>/scripts/analyze.py render <output-dir>/analysis-model.json
python <skill-dir>/scripts/analyze.py digest <output-dir>/analysis-model.json
python <skill-dir>/scripts/analyze.py gate <output-dir>/analysis-model.json
~~~

先填写条款、问题及真实确认。完成建模后逐实体语义审查，再用 digest 结果填写 reviewDigest，重新 render 并 gate。门禁独立核对导出产物、来源哈希、引用、可达性、一对一映射和完整衔接边集。失败修复后重检；缺少用户回答为 BLOCKED。PASS 仅证明本版需求分析完整，不能宣称应用已实现或验收通过。

## 产物

默认项目内 requirements-analysis/，用户指定位置优先：

- analysis-model.json：唯一编辑源，含来源、范围、条款、澄清、状态、迁移、需求、非迁移约束及审查。
- clarification.json / clarification.md：问题、建议、真实确认和未决项。
- state-graph.json / state-graph.md：业务事实节点、操作边与 Mermaid 图。
- atomic-requirements.json / atomic-requirements.md：完整原子需求及功能/视觉字段，附非迁移约束。
- requirement-graph.json / requirement-graph.md：由终态/始态相等生成的需求图。
- gate-report.json / gate-report.md：检查结果、缺失项、阻塞项及语义验证边界。

仅完成分析，不隐含开发、上传或交卷授权。本规范不额外要求用户逐轮批准机械导出或最终分析结果；人工作答发生在真实需求歧义需要决策时。
