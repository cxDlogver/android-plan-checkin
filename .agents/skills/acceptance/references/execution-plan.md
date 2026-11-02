# 验收执行计划与逐项执行

## 1. 准备完成的交付条件

在 route.py init 完成副本、合同和会话索引后，正式执行第一项之前，必须生成并核对验收根目录内的 execution-plan.json、execution-plan.md、execution-plan.html。这是执行清单，不是候选 schedule 输入；以 acceptance.json 为唯一执行事实源，从当前副本和合同派生，不手工维护另一套进度。已有验收索引直接恢复，不重新 init。

清单必须能直接回答：按什么顺序验收、当前在哪一轮、下一次访问是哪一个 Test Case、要做什么、通过后去哪一项、失败或中断时先处理什么。仅给优化原则、文字说明或轮次编号不算交付完成。

| 必须可查询的内容 | 完成判据 |
| --- | --- |
| 固定路线 | visits.caseId 与索引 sequence 逐项相同；保留必要重复；visitIndex 从 0 开始，总序号 order 从 1 开始 |
| 轮次总表 | 每轮 R01、R02… 的闭区间、数量、首尾用例、划分原因、会话及上下文；连续完整覆盖路线且无重叠 |
| 逐项清单 | visitIndex、轮内序号、用例 ID、该用例第几次必要访问、初态、操作、预期、全部适用检查、环境、数据/Mock、合同、前驱与后继 |
| 当前工作 | 从活动访问、有效结果、修复与门禁计算 next.action、canBegin 和唯一 visit；不能用手填“已到第几轮”作为游标 |
| 来源与一致性 | 原索引及副本摘要、合同/会话绑定和确定性 snapshotId；三种清单经 check 与同一源数据一致 |

只根据当前项目计算数量与边界，不在 Skill 中固化某项目的用例数、访问数或轮数。JSON、Markdown 和 HTML 是同一清单的机器、阅读和筛选视图，不能各自维护状态。

## 2. 轮次如何划分与优化

先按[路径与执行规划](route.md)确定固定路线的最少额外进入、准备单元和执行会话，再在该路线内安排连续逻辑轮次。轮次不是进程会话：多轮可以共用同一设备、应用、驱动和数据上下文，不因 R 编号变化重启服务。

默认在路线起点、执行会话起点、当前用例 given 为已声明合法初态、独立用例 fixture 入口切分。两个相邻边界之间的全部访问属于一轮；边界落在原访问之前，不能删减、复制或重排原路线。记录 boundaryReasons，不按任意“每 N 个用例”、相似页面或平均时长强行分组。独立用例仍按自身数据/Mock 隔离规则准备。

连续运行时沿有效实际终态交接，兼容上下文复用准备；到达逻辑轮界不自动引入额外产品动作。会话切换所需 entryReplay 和准备单元按真实会话计划计费。对运行期间的主动停靠，优先选择能以已验证初态和低成本 fixture 恢复的边界；若驱动尚不支持持久化与恢复，标明能力缺口。

“最小开销”必须写明成本与约束：现有调度器只在既定路线及给定、已审查候选能力内，按额外进入访问数、准备单元次数、会话数依次最小化。默认自然轮次是可复现划分，不证明全局最少轮数、最短墙钟时间或任意中断下的最小恢复成本。需要进一步优化中断成本时，先给出实际可恢复点、恢复动作/成本、驱动约束以及允许的停靠条件，再比较候选分组；缺少这些输入时不得声称已求得全局最优。

## 3. 固定工具与执行循环

所有命令沿用同一 workspace 和 record；record 省略时默认 <workspace>/plan/acceptance/acceptance.json。项目入口可以薄封装通用工具，不复制一套查询或分组算法。

~~~text
python -B <skill-dir>/scripts/execution_plan.py sync --workspace <root> --record <record>
python -B <skill-dir>/scripts/execution_plan.py check --workspace <root> --record <record>
python -B <skill-dir>/scripts/execution_plan.py next --workspace <root> --record <record> --json
python -B <skill-dir>/scripts/execution_plan.py round R01 --workspace <root> --record <record>
python -B <skill-dir>/scripts/execution_plan.py list --workspace <root> --record <record>
~~~

1. 运行 route.py check，再 sync/check 执行清单。next 从当前索引实时推导；HTML/Markdown 是快照，不能凭已打开页面或对话记忆确定下一项。
2. 若 next.canBegin 为 true，确认 visitIndex 与 route.py next 一致，按同一下标 begin。观察真实 given、宿主、对象、输入、适用 prerequisite 和 Mock；缺前提如实提交 blocked，不跳到后继。
3. begin 后立即 sync/check，将当前项显示为进行中；完成同一次访问的全部适用检查并逐项取证。单脚本可以循环多例，必须等待当前访问提交完毕。
4. submit 后先要求 passed 且 recorded、synced、checked、canAdvance 全为 true，再 sync/check 执行清单，重新查询 next，才允许进行下一项。失败或阻塞同样即时更新清单并停止；清单同步失败时不得继续产品操作。
5. repair-open、repair-close、close-session、恢复提交以及任何导致有效结果变化的更新后，重建并核对清单。跨会话之前核对前一会话真实成功收尾。逻辑轮次完成只说明该区间全部访问有效通过；仍须核对会话收尾和最终 finish。

驱动必须实际 await 上述门禁和清单同步；本工具只查询并生成文件，不执行应用、不自动暂停、不自动冷重放。route.py 当前不会自动调用 execution_plan.py；未接入的旧驱动必须由外层逐项编排，或先补齐并验证接入。不能将规范、输出 canBegin 或图中边界表述为已部署的自动运行能力。查询成功也不证明宿主实时就绪。

## 4. 中断后从哪里恢复

| 当前事实 | 下一动作与禁止事项 |
| --- | --- |
| active.stage=recorded | 使用相同 runId、token 和原始结果恢复同一次 submit，再同步清单；不重做产品动作来补登记 |
| active.stage=running | 保留授权与现场，核对动作是否已发生；能够证明时完成同一次观察和提交；无法证明时如实记录 blocked 并走修复，不盲目重试副作用 |
| 失败或有未完成修复 | 保持当前最早未通过位置，保存证据并完成 repair-open/repair-close；不执行后继，不删除失败或重建索引 |
| 无活动项，真实状态和上下文仍有效 | 保留所有有效已通过访问，核对当前 given 后从 next 继续，不从本轮开头重验 |
| 设备/进程或数据上下文丢失 | 从允许起点恢复到当前 given；coldResume 仅列状态图上的最短候选前缀，必须再核对对象身份、输入、持久化数据、Mock 生命周期和真实动作；不直接注入目标画面 |
| 源码、脚本、定义或证据变化 | 按真实影响与现有失效判定，从最早受影响访问重验；未受影响且绑定仍有效的结果保留，不通过缩小摘要范围强行复用 |

恢复前缀的操作是重新进入成本，不是对其已通过 Test Case 再次验收；额外动作及实际证据按 entry/replay 记录，不改原 sequence 或将候选当作已执行。图最短不保证动态上下文可恢复；不可行时说明所缺能力并修复恢复链路。当前门禁不支持跳过中间失效的必要访问，不能凭“过去通过过”跨越当前游标。

最小持久化单位是一次正式访问的提交。只有驱动、合同及证据工具已经支持可验证的子检查恢复时，才可以进一步减少单个长用例内的重做成本；不能仅凭规划文件宣称支持。

## 5. 保留与清理

最终保留执行计划三份视图、正式入口、验收索引、合同、隔离副本与必要实际证据。临时候选 schedule、探索性恢复方案、重复中间报告和预览图片在引用迁移与核对后删除；不另建与 acceptance.json 竞争的恢复游标或进度源。仍被正式驱动使用的编译产物、服务临时目录和恢复输入须待引用解除后再清理。
