# 证据与状态

## 1. 正式记录

acceptance.json 由一个汇总者写入，绑定 testCasesPath、taskPlanPath、implementationPath、caseContract、planContract，保存 planningSource、testTypes、sequence、upstream、planning、sessions、scheduleContract、contractsDirectory、currentDefinitions、definitions、active、attempts、repairs 和 sessionResults。planningSource 固定四份只读规划原件及其原始摘要；testCasesPath/taskPlanPath 绑定验收副本。planning 固定已审查候选准备方案与最优成本；definitions 保留各次冻结定义，contractsDirectory 指向每个用例的 JSON 合同。路径相对工作区，Schema 见 [acceptance.schema.json](../assets/acceptance.schema.json)。临时 schedule 输入在初始化并核对后删除，不再维护另一套路线。

### 1.1 默认产物目录

验收根目录默认是 <项目根目录>/plan/acceptance/，不依赖启动命令时的当前目录。显式指定 acceptance.json 的路径时，使用该文件父目录作为本轮根目录；后续命令沿用同一记录路径，不能混写两处。

~~~text
plan/acceptance/
  acceptance.json                  验收计划、来源摘要、访问、修复与会话索引
  execution-plan.json/md/html      轮次、完整逐项顺序与当前下一项的派生清单
  test-cases.json/html              用例定义与状态的验收副本
  task-plan.json/md                 任务关联与可读视图的验收副本
  contracts/<caseId>.json           每个 Test Case 的合同
  scripts/                         本轮新增的正式驱动和验收脚本
  evidence/<attemptId>/            每次实际访问的报告、截图、节点树和上下文
  evidence/<attemptId>/repair/     与该次失败关联的必要修复证据
  evidence/sessions/<sessionId>/   执行会话的真实退出结果与必要日志
  .work/                           候选会话方案、诊断等临时输入
~~~

目录按实际内容创建，不要求预建空目录。已有仓库正式测试脚本可以原位复用并直接引用，不复制到 scripts。证据目录以实际 attemptId/sessionId 区分，避免重复访问覆盖原文件。仅存于临时目录的材料不能作为最终证据。重跑所需的实际配置和输入属于正式材料，应保留在证据目录，不能随 .work 清理。

plan 命令省略输出路径时写入根目录下的 .work/schedule.json；init 省略 --schedule 时读取同一位置。仅修改记录路径不会自动搬迁既有材料，重定向前要核对引用。

任务规划的 test-cases.json/html、task-plan.json/md 保持原件不变，初始化时复制到验收根目录，后续同步只写副本。原 PRD、UI、状态图、原子需求图与实现记录保持正式位置并只读引用。所有证据引用相对项目根目录，支持显式选择其他工作区内的验收根目录。

任务完成且记录与视图核对成功后，删除本轮 .work 内的临时输入和自己创建的草稿；保留 acceptance.json、execution-plan.json/md/html、合同、正式脚本及必要成功/失败/修复证据。仍在恢复中的输入暂留，恢复完成后再清理。

active 保存当前 visitIndex、授权 token、实际开始时点、sessionId、前项记录身份和提交阶段。begin 同步 running；submit 保存一项 run 后同步对应合同、JSON 和 HTML 的终结状态，再写关闭时点并清除 active。只有 active 关闭后才允许后继 begin。相同会话复用进程与宿主，active 仍一次只指向一个访问。

attempts 每项有 run、authorizedAt、predecessorAttemptId、definitionHash、closedAt。definitionHash 绑定该次实际采用的冻结定义；修复后新定义不能覆盖原失败所用定义。run 记录实际脚本及摘要、编写时点、真实命令和工作目录、实际起止时点、进程退出码或 null、环境、taskIds、源码及配置快照、context、恰好一个 visits，taskResults 为空。taskIds 用于定位源码责任，不能代替用例验收；不在这里重新验收 task-plan 的静态检查。

run.environment 为 runtime、native、browser 或 mixed；context.environments 逐个列出实际环境及宿主，native/browser 需要实际 host。context 同时记录 build、inputs、mocks、entry；输入应为本次解析结果，Mock 应有命中和恢复记录，不能只是静态声明。适用 prerequisite 也须有已满足的观察依据，缺失时记录 blocked。

visits 记录 visitIndex、entry、givenObserved、operationObserved、targetObserved、outcome 和 checks。可读说明使用实际观察，不复制预期充当实际。outcome 为 passed、failed 或 blocked，不用 deferred 空访问跳过当前必要检查。进入前即受阻、尚未执行任何检查时，checks 为空并提供 blockage.reason 和 blockage.evidence；断言报告定位 case:<caseId>:entry:<visitIndex>，记录缺少的真实前提，不能假装已经执行 operation。

## 2. 检查证据

每项 checks 用 aspect=visual/functional 与 checkIndex 定位 Test Case 的既有定义，记录 status、actual、evidence。所有本轮适用检查齐全并通过才能将当前访问标为 passed。失败或阻塞可以只记录已实际执行的检查，其余不能预填通过。

evidence 每项包含 form、path、sha256、description，按定义提供截图、DOM、原生节点树、组件树、布局测量、状态快照、数据快照、调用轨迹或断言报告。原设计图作为预期图继续在 HTML 展示，不属于实际 evidence。

每项结果必须引用 assertion-report。报告根包含 assertions；每行包含 target、独立 expected、实际 actual、verdict，target 为 case:<caseId>:<aspect>:<checkIndex>:<visitIndex>。报告判定必须与登记状态一致；文件存在和摘要一致只说明材料完整，仍需审查它能否证明所述结论。

run 的 files 覆盖关联实现任务及其必要依赖、命令配置与锁文件。证据、脚本或源码变化时旧结果不能继续用于放行。只有经过[修复影响审查与完整旧脚本归档](repair.md#5-限定保留未受影响的旧驱动结果)的未受影响历史入口脚本，可按限定规则保留；产品源码及实际结果证据不适用该例外。已经登记的实际证据不可覆盖，修复后追加新 attempt。

## 3. 状态与显示

| 状态 | 判断 |
| --- | --- |
| not_run | 当前版没有对应实际结果 |
| running | 当前访问已授权且正在执行 |
| passed | 全部必要检查和路径访问均已通过 |
| partial | 部分访问或检查已完成，其他仍待验收 |
| failed | 最近适用实际检查失败或本步进程明确非零退出 |
| blocked | 缺少真实前提或必要环境，当前访问无法完成 |
| stale | 当前材料或依赖与实际结果绑定的摘要不同 |

同一用例汇总所有出现次数；每次访问保留独立结果。后续访问尚未发生时保持 partial，但已经通过并同步的当前访问可以按路径继续。更新状态不等于改为 passed，必须依据证据计算。

JSON 是用例状态源，HTML 从同版 JSON 派生。保留已有侧栏规范：到达路径、前置位置、操作、预期结果及 UI 图、验收类型、证据和当前状态；不增加大量文件映射。状态同步时只更新验收副本的 task-plan.testCases 摘要和派生 Markdown，不修改任务规划原件、任务实现状态、来源或原最少路线；预期修订按修复流程在副本中进行。

## 4. 工具入口

以下命令中的记录路径可以省略，默认使用上述验收根目录；需要自定义时显式提供路径。先运行 preflight 核对进入准备阶段的条件，再审查候选准备能力、生成验收执行计划。init 先复制规划产物再生成每例合同；submit 只同步验收副本、合同和验收记录。repair-open/repair-close 使用的诊断和修复字段见[失败与修复](repair.md)。

~~~text
python -B <skill-dir>/scripts/route.py preflight --workspace <root> --cases <规划test-cases.json> --plan <规划task-plan.json> --implementation <implementation.json>
python -B <skill-dir>/scripts/route.py plan <schedule-input.json> --workspace <root> --cases <test-cases.json> --profiles <profiles-input.json> --test-types script
python -B <skill-dir>/scripts/route.py init <record> --workspace <root> --cases <test-cases.json> --plan <task-plan.json> --implementation <implementation.json> --schedule <schedule-input.json> --test-types script
python -B <skill-dir>/scripts/route.py next <record> --workspace <root>
python -B <skill-dir>/scripts/route.py begin <record> --workspace <root> --index <visitIndex>
python -B <skill-dir>/scripts/route.py submit <record> --workspace <root> --token <begin返回的token> --run <当前访问结果.json>
python -B <skill-dir>/scripts/route.py repair-open <record> --workspace <root> --index <visitIndex> --run <原因定位.json>
python -B <skill-dir>/scripts/route.py repair-close <record> --workspace <root> --index <visitIndex> --run <修复复核.json>
python -B <skill-dir>/scripts/route.py close-session <record> --workspace <root> --run <真实进程结果.json>
python -B <skill-dir>/scripts/route.py check <record> --workspace <root>
python -B <skill-dir>/scripts/route.py finish <record> --workspace <root>
~~~

init 后须按[验收执行计划](execution-plan.md)生成清单；每次状态变更后单独运行 execution_plan.py sync/check，再以 next 查询完整工作项。route.py 不自动维护该清单，驱动或外层编排须实际等待同步，不能仅依赖旧快照。

next 只返回当前可执行下标，不执行应用。begin 只允许该下标并同步 running。submit 同步并关闭当前项，返回 recorded、synced、checked、canAdvance；失败已登记也不放行，并进入修复。repair-close 不表示用例通过，修复后仍须从受影响访问重验。finish 要求全部必要访问和适用检查通过、无未关闭访问或提交、无未完成修复，所有会话真实成功收尾，合同和各视图一致。

check 返回 consistent，表示索引、每例合同及视图一致；不是验收 passed。只有 finish 的 passed 可以表示其 scope 内验收完成，仍须人工或模型审查证据语义。只脚本范围完成时明确 browserPending；不报告完整验收完成。

已有批次执行索引的 execution.schema.json 和 execution.py 保留只用于原有记录的证据核对、恢复提交与视图同步；其 check、submit 或局部任务结果都不提供本规范的下一步授权；未登记隔离副本的旧记录禁止 submit/sync，不能写回规划原件。既有结果不得强行转换成逐项完成记录；需要转入新执行时先审查和规划，不能初始化覆盖已有 JSON 状态。
