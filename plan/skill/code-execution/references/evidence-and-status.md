# 证据与状态契约

## 1. 正式产物

同一组任务计划共用一份 execution.json，由单一汇总者写入。execution.json 是执行索引，绑定任务计划与用例的语义摘要；scripts/ 保存正式验收脚本，evidence/<run-id>/ 保存每次运行的必要证据。已有仓库测试目录可直接复用，索引引用工作区相对路径，不重复拷贝脚本或设计截图。

每次运行保存：命令参数数组、工作目录、脚本及摘要、编写与运行时点、退出码、运行环境、覆盖任务、实际文件快照、数据与 Mock 观察记录、连续路线访问、任务局部验收与用例逐检查结果。stdout 日志只在有定位或复现用途时保留。

assertion-report 使用 JSON：根 assertions 数组；每项有 target、expected、actual 和 verdict（passed/failed/blocked）。用例 target 为 case:<caseId>:<aspect>:<checkIndex>:<visitIndex>，任务 target 为 task:<taskId>:<checkIndex>；这是既有检查的定位键，不是新增需求身份。共享报告按 target 分别匹配。

每份证据包含 form、path、sha256、description；检查结果必须引用 assertion-report，内容有检查目标、独立预期、实际观察及 verdict。一个报告或截图可被多项检查引用，但每项说明它证明什么。文件存在和摘要一致仅证明证据完整性，结论仍需审查。

截图来自本次实际宿主；原生节点树标明 native-tree；浏览器 DOM 属于浏览器验收，本流程不采集。运行器仅提供它实际观察到的组件树、状态或调用。原设计截图是预期参考，不属于 execution.evidence。

## 2. 记录字段

[执行 Schema](../assets/execution.schema.json)约束以下结构：

| 对象 | 记录 |
| --- | --- |
| 根 | schemaVersion、testCasesPath、taskPlanPath、caseContract、planContract、tasks、runs |
| tasks[taskId] | implementation 为 null 或 {startedAt,completedAt}；resources 为独占资源名数组 |
| run | id、taskIds、script、authoredAt、command、cwd、startedAt、finishedAt、exitCode、environment、files、context、visits、taskResults |
| script/files/context | {path,sha256}；files 覆盖关联任务及其依赖的全部声明文件、命令配置与锁文件；context 保存实际输入、Mock 命中/恢复、宿主与构建版本 |
| visit | visitIndex、entry、givenObserved、operationObserved、targetObserved、outcome、checks；entry 是合法起点准备或前次已观察终态的说明 |
| checks | aspect、checkIndex、status、actual、evidence；只定位已有 script 检查 |
| taskResults | taskId、checkIndex、doneIndices、status、actual、evidence；定位计划 checks 与 done |

context 是 JSON，包含 environment、build、inputs、mocks、readyPrerequisites；原生运行还记录实际设备或模拟器的唯一 host 标识。readyPrerequisites 是本次有证据表明已具备的计划前置项 ID，不用空声明代替资源准备。

aspect 为 visual/functional；checkIndex 与 doneIndices 从 0 开始。actual 是可读的观察结论，不是复制预期。运行记录一旦提交不重写证据文件；修复后追加新 run。

## 3. 状态归并

| 状态 | 判断 |
| --- | --- |
| not_run | 没有本版有效实际结果 |
| running | 当前正在执行，不能报告完成；工具只同步已落盘的终结结果 |
| passed | 本次需要的全部检查、证据和路线访问已通过 |
| failed | 最近有效执行的相关检查失败，或进程非零退出 |
| partial | 部分检查或访问通过，仍有未执行项；浏览器检查在本阶段保持待验收 |
| blocked | 缺少前提或宿主，不能执行；记录原因，不改成失败断言 |
| stale | 代码、脚本、输入或证据摘要变化，旧结论失效 |

完整用例聚合全部覆盖路线出现次数的所有适用检查；同一访问重试以最近有效 run 为准，不能用旧通过覆盖新失败。多个脚本共同覆盖一例时汇总检查，不能由最后一个脚本直接覆盖整例状态。浏览器检查不产生结果；脚本均通过但仍有浏览器项则 partial。

任务状态 planned、implemented、partial、passed、failed、blocked、stale 由任务实现记录、计划 checks 和 done 覆盖汇总。只有本任务全部局部脚本检查通过且 done 逐项有证据时为 passed。依赖就绪读取此状态，不读取宽泛的用例映射是否全部通过。

用例 execution.actual 显示中文可读摘要；execution.evidence 汇总带来源运行的实际证据；execution.checks 保存每次访问的逐项状态、实际观察与证据。HTML显示当前状态与证据链接，并保留到达路径、前置条件、操作、预期 UI 图和逐检查要求。侧栏不扩展成文件映射清单。

## 4. 工具与同步

所有路径参数以工作区为边界；工具本身可从任意位置调用。示例命令中的 python 可换为当前可用的 Python 运行器：

~~~text
python -B plan/skill/code-execution/scripts/execution.py init plan/code-execution/execution.json --workspace . --cases plan/task-planning/test-cases.json --plan plan/task-planning/task-plan.json
python -B plan/skill/code-execution/scripts/execution.py ready plan/code-execution/execution.json --workspace .
python -B plan/skill/code-execution/scripts/execution.py sync plan/code-execution/execution.json --workspace .
python -B plan/skill/code-execution/scripts/execution.py check plan/code-execution/execution.json --workspace .
python -B plan/skill/code-execution/scripts/execution.py finish plan/code-execution/execution.json --workspace .
~~~

init 在编码前执行规划检查并记录不可变语义摘要；resources 初始为 unreviewed-resources，核对实际资源后改为明确资源数组，无共享资源才置空。已有记录拒绝覆盖。任务实现后写 implementation，脚本结束后将真实结果追加 runs，再执行 sync。sync 校验后同时生成用例 JSON、任务 JSON、HTML 和 Markdown；更新 task-plan.testCases 摘要，不改变来源、预期或路线。single-writer 由调用方保证；工具使用独占锁防止两个同步进程并发写。中断后再次 sync 可恢复视图，不能手工给 HTML 单独改状态。

check 只读核对契约、证据与已生成视图。finish 另核对所有任务局部验收通过，以及脚本验收所需的全部路线访问；浏览器待验收单独列出，不算本阶段已完成浏览器验收。

规划 Schema 允许执行状态，但任务规划工具仍仅接受初始 planned/not_run；执行后使用本工具复查，不能把原始代码证据摘要更新为新代码来绕过规划门禁。原始 codeEvidence，以及 dataProfiles.fields[].source、prerequisites.source 中指向计划修改代码的引用，保留为实施前依据；其来源在 init 校验并由计划契约固定，实施后不按旧摘要重复校验已修改代码。run.files 记录实际验收版本，就绪情况由实际运行上下文及证据确认。必要规划调整须回到任务规划，重新审核契约并使受影响旧证据失效，不直接改摘要继续沿用旧通过结果。
