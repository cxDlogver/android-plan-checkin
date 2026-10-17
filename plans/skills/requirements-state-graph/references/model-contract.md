# 结构化模型契约

## 唯一编辑源与版本

analysis-model.json 是唯一需求编辑源，JSON 使用 UTF-8。先编辑工作副本，通过 checkpoint 才成为已提交模型；恢复以 current.json 指向的检查点为准。导出和 HTML 来自同一 revision 和摘要。ID 稳定且全局不重复，删除后不复用旧含义。

模型顶层字段：

| 字段 | 结构／含义 |
| --- | --- |
| schemaVersion | 固定为 2 |
| revision | 非空模型版本 ID；任何结构或需求含义变化均递增／更换 |
| phase | clarifying、analyzing、review_ready、confirmed、incomplete |
| scope | objective、included[]、excluded[]、abstraction；描述本次功能与状态抽象边界 |
| sources[] | id、kind（prd/ui/human）、uri、locator、version；另含 evidencePath、sha256、readRanges[]；见下文 |
| features[] | id、title、scope、entryStateIds[]；按业务能力组织，不强制一组功能等于一个连通分量 |
| states[] | id、featureIds[]、title、facts[]、uiRefs[]、sourceIds[]、status；可选 questionIds[] |
| transitions[] | id、featureIds[]、from、event、guard、to、requirementId、sourceIds[]、status；可选 questionIds[] |
| requirements[] | id、transitionId、title、ruleIds[]、acceptance[]、uiRefs[]、uiApplicability、sourceIds[]、status；可选 questionIds[] |
| questions[] | id、question、blocking、status（open/resolved/out_of_scope）、affectedIds[]；解决时填 resolution、humanReference |
| confirmations[] | stage（scope/final）、revision、humanReference、summary；scope 必须 scopeDigest；传统 final 必须 semanticDigest、coveredIds[] |
| rounds[] | id、revision、nodeIds[]、checks[]、changes[]、openFrontier[] |

实体 status 为 draft、candidate、confirmed。draft 表示依据资料推导的待最终验收内容；candidate 表示依赖未定解释的可选方案。二者都不是人工确认。confirmed 只能在当前版本最终获人工确认后写入。

scope 确认绑定 scopeDigest（model_tools.py scope-digest），相同范围跨 revision 仍有效，范围改变须新人工确认。正常交付用独立 acceptance.json 绑定语义／包／报告摘要和全部状态、迁移、需求 ID，见 workflow.md。冻结快照保留当时 draft 和 review_ready，正式确认由 acceptance 与 gate-result 表达。传统 phase=confirmed 模型仍须当前 revision 的 final 确认和 semanticDigest，但结构通过不代表完整门禁通过。不得编造回复或对话引用。

## 状态与迁移

facts[] 用非空文字明确记录当前业务事实和有验收意义的 UI 表现。目标状态表达此次迁移的结果；迁移边不得混写“显示某提示／数据已保存”等结果或状态修改指令。

guard 是明确的条件表达，无法定义时不得伪造谓词。无附加条件可写 true。事件与守卫分开，例如 event=点击提交，guard=未处理项数大于0。条件语义及来源需可追溯；脚本不执行任意 guard 字符串，也不假装自动证明任意谓词完备。

允许平行边、循环、共享节点和不连通图。相同 from/to 不表示两条边等价；事件或守卫不同仍是独立迁移。抽象事实相同且行为、可观察响应及后续能力相同的节点应复用。

提示出现、弹窗打开、禁用／只读等若影响验收，可以成为状态差异。若定义的全部状态维度均未改变，可保留自环；不得一面声称 UI 状态已变化，一面仍用同一节点隐藏它。持续成立的视觉规范或不变量挂在状态／验收约束上，不为凑“一迁移一需求”制造虚假业务事件。

## 原子需求与衔接图

每条迁移恰有一个 requirementId，每项需求恰引用一个 transitionId，双向引用必须一致。相同业务规则可复用 ruleIds[]，但不同迁移不合并为一个原子需求。完整链路是多个需求的引用序列。

ruleIds[] 使用来源中可定位的规则／条款 ID，通过 sourceIds 找到其定义；资料没有稳定规则 ID 时留空，不伪造一套无出处的规则编号。

requirements[] 不重复存储 from/event/guard/to，避免两份真相；导出及 HTML 应解析 transitionId，展示完整的起点—事件／条件—终点结构。

acceptance[] 每项含 id、given、when、then[]。一个迁移行为可包含共同成立的多个断言；禁止副作用须显式写出，例如“不发出提交请求”，不能仅凭页面终态认为已验证。本文要求需求的验收语义，不要求生成自动化测试或完整 Test Case 工程。

原子需求图节点 R 来自 requirements[]。对任意 Ri、Rj，当且仅当 to(Ri) == from(Rj) 时生成一条 continuation 边，记录 viaStateId。含自环或回环时仍按同一公式处理，不截断数据图。

该边代表在当前抽象状态层面可衔接，后续事件与守卫仍需满足；不表示任意数据实例都能连续执行，不表示开发先后、规则依赖或已证明路径可满足。若守卫暴露状态抽象混淆，回到状态模型细化，不让 AI 私自画另一种关系图。

## UI 对应与来源

uiRefs[] 每项包含 sourceId、frameId、region、stateLabel。sourceId 必须引用 kind=ui 的来源；region 应定位到具体组件／区域，必要时补 screenshot 或节点 ID，不能只写“见 UI”。

uiApplicability 是对象：

- status=mapped：至少一个有效 uiRef，可追溯视觉场景。
- status=not_applicable：本项无可见 UI，reason 说明理由，不能用它掩盖缺稿。
- status=missing：存在可见 UI 但缺少依据，reason 说明缺口，decisionQuestionId 关联待决问题；最终须补齐，或由用户明确接受其限制／移出范围并记录问题处置。

状态也保存 uiRefs，以展示不同业务状态对应同页不同视觉状态。公共颜色、字体与尺寸可引用同一设计规范，不必复制成新的原子需求。没有 UI 依据时保留 missing，不虚构控件、默认值、文案或稿外页面。

sourceIds[] 至少一个，来源可以是用户指定资料或本轮明确人工作答。candidate 还必须关联 questions[]，并明确支持证据与待决定部分。附件中的旧 assistant 推断不是当前确认记录。

evidencePath 是相对 RUN 的实际缓存路径（不可越界），sha256 为字节摘要，readRanges 是非空读取范围（章节、页码、行号或画板区域），不能用缓存存在冒充已读。图片缓存可预览 PNG/JPEG/GIF/WebP；非图片原稿可加 previewPath、previewSha256 保存截图。HTML 内嵌预览；无可预览图则保留原稿定位，不能冒充视觉已核对。每来源须有 source 或 decision 检查点记录读取／决定。

问题 affectedIds 可指状态／迁移／需求／功能或 scope；未知 ID 拒绝。状态／迁移／需求与问题的 questionIds/affectedIds 双向一致，包括已解决问题。blocking=false 不能绕过最终开放问题检查。正式基线不含 open 问题或 candidate；移出范围须从正式模型去除受影响候选并保留处置历史。

## 循环审查记录

每轮以 revision 绑定快照。nodeIds[] 为本轮开始时全部状态 ID；新增节点放入下一轮，修改节点和受影响邻居也重新检查。

每轮还含 kind（build/audit）。checks[] 每项含 nodeId、dimension、disposition、reason、evidenceIds[]、relatedIds[]。dimension 与 disposition 使用 branch-review.md 中的约定。changes[] 含 kind（add/update/remove）、entityId、meaning、sourceIds[]；无新增且无修改为 []。openFrontier[] 保存本轮结束仍需分析的实体／问题 ID。

nodeId 必须在该轮 nodeIds 快照；relatedIds 与 openFrontier 可解析。历史删除对象以该轮 retiredIds[] 保留 ID，须有 remove 的 changes、来源和 meaning，不用凭空 retiredIds 掩盖错字。闭合轮只覆盖当前全部状态；同维度允许多条检查。

最终闭合 audit 另记录 modelDigest。用 model_tools.py digest 计算；摘要包含 revision、范围、来源、功能、状态、迁移、需求与问题，排除审查／确认元数据及实体确认 status。这样更新人工确认状态无需改变语义版本，但改动行为、UI 对应、验收或问题解释后必须重审。

允许未决业务问题留至最终验收，但不能把“该问题已有唯一答案”作为继续推导的前提；依赖它的内容维持 candidate 并关联问题。结构不确定的分支留在问题记录，不制造看似真实的占位状态。

## 脚本导出契约

scripts/model_tools.py 从唯一模型导出以下文件，每个文件都带 schemaVersion 和 revision：

- state-graph.json：scope、sources、features、nodes、edges。
- atomic-requirements.json：requirements，并解析 featureIds、sourceState、transition、targetState 和完整 statement，便于独立阅读。
- requirement-graph.json：feature 分组、原子需求节点、continuation 边；不加入其他边类型。
- review-log.json：phase、scope、questions、confirmations、rounds 及结构检查摘要。

导出前进行结构检查；结构通过不等于业务已确认。--final 还检查当前版本人工确认记录、待决项、实体状态和完整闭合轮。程序仅验证记录一致性，无法认证 humanReference 的真实性或证明业务语义正确。

所有 JSON 带 schemaVersion=2、revision、semanticDigest。衔接边 ID 为 C: 加紧凑 JSON 二元组 [前项ID,后项ID]，不用有歧义的冒号拼接。export 输出新整包目录（含 HTML、图片和 manifest），拒绝覆盖。正式交付须 workflow.py publish。

## v1 显式迁移

保留原模型和证据，另 init 新运行；复制需求，schemaVersion 改 2，核对来源补真实缓存／读取范围、scopeDigest、双向问题关联和删除记录。没有过去过程证据就从本次实际补读、补审并 checkpoint，不伪造过去步骤。旧闭合／报告／最终确认不自动通过新门禁，重新独立验收；已有真实回复可按其覆盖范围复用，不重复询问相同已确认事项。
