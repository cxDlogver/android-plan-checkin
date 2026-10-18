# 结构化模型契约

## 唯一编辑源与内容摘要

RUN/_process/analysis-model.json 是唯一需求编辑源，JSON 使用 UTF-8。增量修改直接写入该工作文件，再运行 save 校验当前状态。RUN/analysis-model.json 是供后续阶段消费的生成结果，不独立编辑。导出与 HTML 同源重建，使用内容摘要对账。不保存进度快照，不强制版本字段或递增编号。ID 稳定且全局不重复，删除后不复用旧含义。

模型顶层字段：

| 字段 | 结构／含义 |
| --- | --- |
| schemaVersion | 固定为 2 |
| phase | clarifying、analyzing、review_ready、confirmed、incomplete |
| scope | objective、included[]、excluded[]、abstraction；描述本次功能与状态抽象边界 |
| sources[] | id、kind（prd/ui/human）、uri、locator；version 仅在来源已明确时记录，另含 evidencePath、sha256、readRanges[]；见下文 |
| pathContext | 可选有限域链路约束，含 domains、entryContexts、transitionRules 和可选 stateConstraints；共享状态会混淆来源/类型/操作方式时须补充或细分状态，见下文 |
| entryStateIds[] | 文档明确的全局业务起始状态 ID；有状态时非空，不等于功能组入口，不按零入度猜测 |
| features[] | id、title、scope、entryStateIds[]；按业务能力组织，不强制一组功能等于一个连通分量 |
| states[] | id、featureIds[]、title、facts[]、uiRefs[]、sourceIds[]、status；可选 questionIds[] |
| transitions[] | id、featureIds[]、from、event、guard、to、requirementId、sourceIds[]、status；可选 questionIds[]；from=to 时必须 selfLoopEvidence |
| requirements[] | id、transitionId、title、ruleIds[]、acceptance[]、uiRefs[]、uiApplicability、sourceIds[]、status；可选 questionIds[] |
| questions[] | id、question、blocking、status（open/resolved/out_of_scope）、affectedIds[]；解决时填 resolution、humanReference、decisionSourceId（kind=human） |
| confirmations[] | stage（scope/final）、humanReference、summary；scope 必须 scopeDigest、sourceId（kind=human）；如在模型内记录 final 则必须 semanticDigest、coveredIds[] |
| rounds[] | id、kind（build/audit）、nodeIds[]、checks[]、changes[]、openFrontier[]；audit 含 modelDigest |

实体 status 为 draft、candidate、confirmed。draft 表示依据资料推导的待最终验收内容；candidate 表示依赖未定解释的可选方案。二者都不是人工确认。confirmed 只能在当前内容最终获人工确认后写入。

scope 确认绑定 scopeDigest（model_tools.py scope-digest），相同范围在内容更新后仍有效，范围改变须新人工确认。正常交付用独立 acceptance.json 绑定语义／包／报告摘要和全部状态、迁移、需求 ID，见 workflow.md。当前评审模型可保留 draft 和 review_ready，正式确认由匹配当前摘要的 acceptance 与 gate-result 表达。若模型标记 phase=confirmed，须具备覆盖当前语义摘要的真实 final 确认；结构通过不代表完整门禁通过。不得编造回复或对话引用。

## 状态与迁移

顶层 entryStateIds 声明需求文档明确的全局业务起始状态，功能组的 features.entryStateIds 仅说明局部进入状态。两者不得混用；有回环的全局起点仍是起点，不能按零入度自动猜测。真实起点可为一个或多个，每个起点的 sourceIds 及其资料定位须能说明起始场景；无依据的“启动／加载”技术阶段不自动成为需求起点。全图须保留从起点不可达的状态并标出待复核，按 branch-review.md 处置；缺失链路不能通过给该状态添加起点身份来掩盖。状态、事件、条件和预期结果用完整中文说明；内部 ID 仅供关联。

facts[] 用非空文字明确记录当前业务事实和有验收意义的 UI 表现。目标状态表达此次迁移的结果；迁移边不得混写“显示某提示／数据已保存”等结果或状态修改指令。

guard 是明确的条件表达，无法定义时不得伪造谓词。无附加条件可写 true。事件与守卫分开，例如 event=点击提交，guard=未处理项数大于0。条件语义及来源需可追溯；脚本不执行任意 guard 字符串，也不假装自动证明任意谓词完备。

允许平行边、循环、共享节点和不连通图。相同 from/to 不表示两条边等价；事件或守卫不同仍是独立迁移。抽象事实相同且行为、可观察响应及后续能力相同的节点应复用。

提示出现、弹窗打开、禁用／只读等若影响验收，可以成为状态差异。自环仅在原文支持独立可核验的响应／约束、且同一参数化状态类别能够正确表达前后事实时保留；不得因重复点击不换页就自动建边，也不得用自环隐藏需要另行表达的 UI 或权限变化。持续成立的视觉规范或不变量挂在状态／验收约束上，不为凑“一迁移一需求”制造虚假业务事件。

selfLoopEvidence 包含非空 sourceRefs[]（各项 sourceId、locator）、obligation 和 stateReason；非自环不得带此字段。sourceRef 必须引用该迁移已列出的来源，并定位到支持该义务的条款／区域。来源支持、独立义务和状态抽象是否合理由独立模型逐条核对，程序只验证结构与引用一致。详见 branch-review.md。


## 有限域链路上下文

pathContext 为已有业务守卫的机器可核对投影，不新增业务规则，不取代中文条件。无需依赖上下文的简单图可省略；共享节点使互斥类别可能串链时，使用此结构或细分状态，不能直接宣称普通BFS结果可执行。

- domains：变量名映射为 values[]、labels{枚举:中文}、description。只记录影响后续能力的有限类别，不穷举实际日期或字段值。
- entryContexts：恰覆盖顶层真实起点，值为{变量:[允许枚举]}。未限制变量保留完整有限域，代表分支可能性，不代表任意实际数据均满足。
- stateConstraints：按状态 ID 保存 requires、sourceRefs、reason，表达该状态始终成立的事实；来源须属于该状态的 sourceIds。进入、离开及入口初始化时均应用。详见 feasibility.md。
- transitionRules：恰覆盖当前全部迁移。每条含 cases[]、sourceRefs[]（sourceId、locator）和 reason；来源须属于该迁移的sourceIds。无相关改变的迁移可用空case，但需说明保持的上下文。来源是否支持条件与效果由独立模型审查。
- case 仅含 requires、set、setFrom、forget。requires 将当前域与允许值求交，空交集拒绝。set 为原文事件实际选择/改变的值；forget 仅在该事件确实使旧绑定失效时恢复完整域。setFrom 从本次所有效果执行前的上下文将同义枚举复制到另一变量，多值逐值分支以保持相关性；不支持异名业务映射或执行表达式。同一目标不得同时被多个效果写入。
- cases 表达析取，各自独立求交，不将相关变量的集合随意合并。禁止为了制造可达路径而set一个没有数据变化来源的事实，例如从无计划切换入口就变为有计划。

链路在“状态＋有限域上下文”上稳定广度优先，按迁移数最少。逐根输出到全部状态的结果；结构孤立、上下文条件冲突和搜索未完成应区别。资源限制触发时不能把未搜索完的状态标成不可达。具体日期、集合成员等未编码条件仍以中文前提保留并接受语义审查，不宣传一般守卫已获形式证明。

pathContext 纳入语义摘要，并随 state-graph.json 导出；修改后旧审查和人工确认失效。需求图的候选衔接公式仍为终态ID等于初态ID，随后按 requirement-graph.md 求连续覆盖路线并投影实际用边；不能用路径上下文随意改变候选关系。结构最优与条件重放分别验收，后项执行仍须满足自己的条件。

## 原子需求与衔接图

每条迁移恰有一个 requirementId，每项需求恰引用一个 transitionId，双向引用必须一致。相同业务规则可复用 ruleIds[]，但不同迁移不合并为一个原子需求。完整链路是多个需求的引用序列。

ruleIds[] 使用来源中可定位的规则／条款 ID，通过 sourceIds 找到其定义；资料没有稳定规则 ID 时留空，不伪造一套无出处的规则编号。

requirements[] 不重复存储 from/event/guard/to，避免两份真相；导出及 HTML 应解析 transitionId，展示完整的起点—事件／条件—终点结构。

acceptance[] 每项含 id、given、when、then[]。一个迁移行为可包含共同成立的多个断言；禁止副作用须显式写出，例如“不发出提交请求”，不能仅凭页面终态认为已验证。每个断言须能按资料判定是否满足，未知要求保留待决；不得用“按各分支处理”等无可解析引用代替结果。验收点必须有来源义务，不因常见异常、缺少画板或分解数量新增要求。原子需求是行为要求，acceptance 是判定该行为是否满足的标准，两者不能混称；一项需求可以有多个共同成立的验收断言。需求数量不代表验收断言数量，更不代表已经通过。各断言应有明确前提、触发和可核对的预期结果；未定义的结论如实待决，不以字段齐全代替可判定。本文要求需求的验收语义，不要求生成自动化测试或完整 Test Case 工程。

原子需求图节点 R 来自 requirements[]。对任意 Ri、Rj，当且仅当 to(Ri) == from(Rj) 时生成候选 continuation 边，记录 viaStateId。候选图包含符合公式的自环与回环，但仅作为生成中间数据；最终 requirement-graph.json 只保留从真实起点派生入口需求的连续覆盖路线实际使用的有向边，详见 requirement-graph.md。状态图中的业务回环及全部原子需求仍保留。

最终保留的边必须来自至少一段已验证的连续路线；各边见证所属上下文可能不同，不能任意拼接用边集合得到新路线。后续事件与守卫仍需满足；不表示任意数据实例都能连续执行，不表示开发先后、规则依赖或已证明路径可满足。若守卫暴露状态抽象混淆，回到状态模型细化，不让 AI 私自画另一种关系图。

## UI 对应与来源

uiRefs[] 每项包含 sourceId、frameId、region、stateLabel。sourceId 必须引用 kind=ui 的来源；region 应定位到具体组件／区域，必要时补 screenshot 或节点 ID，不能只写“见 UI”。

uiApplicability 是对象：

- status=mapped：至少一个有效 uiRef，可追溯画板、文字规定或共享设计规范；只表示引用存在，不表示具体视觉已完整定义或通过验收。
- status=not_applicable：本项无可见 UI，reason 说明理由，不能用它掩盖缺稿。
- status=missing：资料明确要求的 UI 效果缺少所需依据或有冲突，reason 说明义务与缺口，decisionQuestionId 关联待决问题；最终由用户处置。不能仅因没有独立画板，把资料未要求的图形、布局或动画列为必须补充的验收点。

状态也保存 uiRefs，以展示不同业务状态对应同页不同视觉状态。公共颜色、字体与尺寸可引用同一设计规范，不必复制成新的原子需求。没有 UI 依据时保留 missing，不虚构控件、默认值、文案或稿外页面。

sourceIds[] 至少一个，来源可以是用户指定资料或本轮明确人工作答。candidate 还必须关联 questions[]，并明确支持证据与待决定部分。附件中的旧 assistant 推断不是当前确认记录。

evidencePath 是相对 RUN、位于 _process/evidence/ 内的实际缓存路径（不可越界），sha256 为字节摘要，readRanges 是非空读取范围（章节、页码、行号或画板区域），不能用缓存存在冒充已读。图片缓存可预览 PNG/JPEG/GIF/WebP；非图片原稿可加 previewPath、previewSha256 保存截图。HTML 内嵌预览；无可预览图则保留原稿定位，不能冒充视觉已核对。每读完一个来源就更新当前 sources 条目，将读取范围、观察或真实人工作答保存至工作模型与 _process/evidence/；不另建检查点。

问题 affectedIds 可指状态／迁移／需求／功能或 scope；未知 ID 拒绝。状态／迁移／需求与问题的 questionIds/affectedIds 双向一致，包括已解决问题。blocking=false 不能绕过最终开放问题检查。正式基线不含 open 问题或 candidate；移出范围须从正式模型去除受影响候选并保留处置历史。

## 循环审查记录

每轮以 modelDigest 绑定所审语义内容。nodeIds[] 为本轮开始时全部状态 ID；新增节点放入下一轮，修改节点和受影响邻居也重新检查。

每轮还含 kind（build/audit）。checks[] 每项含 nodeId、dimension、disposition、reason、evidenceIds[]、relatedIds[]。dimension 与 disposition 使用 branch-review.md 中的约定。changes[] 含 kind（add/update/remove）、entityId、meaning、sourceIds[]；无新增且无修改为 []。openFrontier[] 保存本轮结束仍需分析的实体／问题 ID。

nodeId 必须在该轮 nodeIds 集合；relatedIds 与 openFrontier 可解析。历史删除对象以该轮 retiredIds[] 保留 ID，须有 remove 的 changes、来源和 meaning，不用凭空 retiredIds 掩盖错字。闭合轮只覆盖当前全部状态；同维度允许多条检查。

每轮 audit 开始时记录 modelDigest，闭合时再次核对。用 model_tools.py digest 计算；摘要包含范围、全局业务起点、requirementTraversal 重启政策、来源、功能、状态、迁移、需求与问题，排除审查／确认元数据及实体确认 status。这样更新人工确认状态无需改变语义摘要，但改动行为、UI 对应、验收或问题解释后必须重审。

允许未决业务问题留至最终验收，但不能把“该问题已有唯一答案”作为继续推导的前提；依赖它的内容维持 candidate 并关联问题。结构不确定的分支留在问题记录，不制造看似真实的占位状态。

## 脚本导出契约

scripts/model_tools.py 从 _process/ 中的唯一工作模型在输出根目录导出以下文件，每个文件都带 schemaVersion 和 semanticDigest：

- state-graph.json：scope、entryStateIds、sources、features、nodes、edges，以及模型存在时的 pathContext。
- atomic-requirements.json：requirements，并解析 featureIds、sourceState、transition、targetState 和完整 statement，便于独立阅读。
- requirement-graph.json：feature 分组、全部原子需求节点、覆盖路线实际使用的 continuation 边及 usageCount、reduction 覆盖/删边信息、traversal 连续路线/访问次数/条件校验/结构最优证书。字段详见 requirement-graph.md；重启作为分段边界，不加入虚拟业务节点或箭头。
- review-log.json：phase、scope、questions、confirmations、rounds 及结构检查摘要。

导出前进行结构检查；整体交付还须满足 gate-rules.md 的确定性、独立模型与人工确认条件。程序仅验证记录一致性，无法认证 humanReference 的真实性或证明业务语义正确。

上述四份结构化视图均带 schemaVersion=2、semanticDigest。根目录 analysis-model.json 原样保留工作模型的字段，不额外注入摘要；manifest.json 按 workflow.md 记录文件摘要与包摘要，不适用这四份视图的字段契约。衔接边 ID 为 C: 加紧凑 JSON 二元组 [前项ID,后项ID]，不用有歧义的冒号拼接。export 在 RUN 根目录重建当前交付（含内嵌图片的 HTML 和 manifest），允许更新同名产物；临时生成文件仅在 _process/ 内创建。正式交付须 workflow.py publish。


## 连续覆盖政策

可选 requirementTraversal 对象含 restartPolicy（none 或 documented_entries）；省略时为 none。允许重启必须记录非空 authorization，指向真实用户决定或来源位置。当前算法固定每次需求访问成本为 1、重启成本为 0；不接收未实现的成本设置。政策参与语义摘要，改变后旧路线、评审和确认失效。结构最优和业务条件校验分别记录，详见 requirement-graph.md。
