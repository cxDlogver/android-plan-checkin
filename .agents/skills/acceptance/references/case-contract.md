# 每个 Test Case 的 JSON 合同

## 1. 一例一份，先确定要求再记录实际

初始化验收时，为每个 caseId 生成 contracts/<caseId>.json；文件名不适合作为路径时使用确定性摘要。重复访问仍共用同一合同，分别按 visitIndex 保存结果。合同是正式最终产物，不是任务完成后删除的中间报告。

合同由验收副本中的正式 Test Case 定义和 acceptance.json 中的实际记录派生；任务规划原件只读。只维护一个可计算的状态来源，不手改合同里的预期、实际或 verdict。Schema 见 [test-case-contract.schema.json](../assets/test-case-contract.schema.json)。

## 2. 字段含义

| 字段 | 记录 |
| --- | --- |
| caseId、title | 既有用例身份及可读标题 |
| source | 验收副本 test-cases.json 路径及定义摘要；摘要固定用例定义和所用数据规范，排除执行状态 |
| definition | 初态、操作、预期结果、视觉/功能检查、判定方法、所需证据、数据规范和 Mock 的验收前快照 |
| stateGraph、givenState、expectedState | 正式状态图引用，以及原初态/终态的事实；视觉事实仍关联原 UI 结构和参考截图 |
| requiredVisits | 该用例在原路径中所有必要访问下标 |
| attempts | 每次真实访问的定义摘要及快照、初态观察、操作、终态观察、时间、检查、比对和证据，保留失败与重试 |
| execution | 当前汇总状态和证据，与 test-cases.json/html 一致 |
| repairs | 与本例相关的原因分析、依据、修复及复核结果 |

definition 内来源仍按 source 指向的原文档位置解析；实际 evidence.path 统一相对工作区。不能从合同文件所在目录错误解析原 UI 来源。

## 3. 预期、实际与证据比对

每项检查以 aspect 和 checkIndex 定位原定义，记录可读 observation、comparisons 和 evidence。comparisons 每项有 expected、actual、verdict，从对应实际断言报告提取，不能只写“通过”而不保留比较双方。

验收前确定判据与预期计算方法。输入依赖对象、时钟、前序数据或环境时，每次访问从明确上下文独立解析具体 expected，不固定设计稿样例，不用实际结果反推 expected。初始化时没有实际观察则 attempts 为空，不预填 actual 或 passed。

证据按用例要求提供 assertion-report、截图、DOM、原生节点树、布局、状态或调用快照等；每份记录 path、sha256、form、description。断言报告按 case:<caseId>:<aspect>:<checkIndex>:<visitIndex> 定位，每行保留 expected、actual、verdict。实际材料失效时不能继续证明通过。

## 4. 更新、修订与门禁

begin 同步 running，submit 同时更新当前用例合同、验收副本 test-cases.json 和副本 HTML；同步的 task-plan.json/md 也只使用验收副本。失败、阻塞、partial、stale 同样同步；状态变化不是必须改成 passed。每次访问已通过并同步，才能按路径继续。

合同缺失、内容与正式定义或实际记录不一致、必要比对/证据缺失，都不能放行。check 和 finish 都检查合同及视图一致性，不能只检查主 JSON。

预期修订必须通过修复流程，从正式 Test Case 更新合同定义，保留原定义快照和失败实际；旧结果失效后重验。修复或定义更新不产生通过结论，不能覆盖原失败图片、节点树、报告或比较值。
