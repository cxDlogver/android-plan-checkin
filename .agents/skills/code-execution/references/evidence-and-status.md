# 实现记录契约

## 1. 字段

implementation.json 只记录代码实现与静态检查。taskPlanPath 指向 task-plan.json，planContract 固定计划语义；生成视图摘要、任务状态和检查状态不计入语义。

tasks 以任务 ID 为键，每项包含：

| 字段 | 含义 |
| --- | --- |
| implementation | null，或实际 startedAt、completedAt；完成时点表示当前实现完成 |
| resources | 实现与静态命令独占资源；明确无共享资源时为空 |
| done | 按 task-plan.done 下标记录 index、observation、sources，说明实现位置和实际改动 |
| files | 当前任务及前置依赖所需的源文件、检查配置和锁文件的 path、sha256 |
| checks | 实际静态命令记录；kind 为 typecheck、lint、format-check、static-analysis |

sources 和 files 使用工作区相对路径及真实 SHA-256。来源可定位不等于语义已完成，仍需审查实际代码。

checks 每项有 kind、command 参数数组、cwd、startedAt、finishedAt、exitCode、log、files。log 为实际输出文件的 path、sha256；files 固定被检查源码及配置。一个命令覆盖多个任务时可以共同引用同一日志。重复相同 kind、command、cwd 的运行，以最近一次适用结果判定，失败原始输出保留。

适用检查在运行前确定，不因运行失败删除检查。工具不能识别所有命令别名背后的行为，先审查命令配置；不适用项在 done.observation 中说明具体原因。

## 2. 状态与门禁

| 状态 | 条件 |
| --- | --- |
| planned | 尚无完整实现记录 |
| partial | 有实现记录，done、文件快照或适用静态检查尚未齐全 |
| failed | 当前适用检查非零退出 |
| stale | 当前源码、配置或证据摘要与记录不一致 |
| implemented | done 已覆盖、顺序有效、适用静态检查全部通过且证据有效 |

检查未执行时保留待完成；缺少工具或输入时说明阻碍，不填零退出码。implemented 与验收 passed 是不同结论。

ready 返回前置任务均为 implemented 且资源已核对的任务组。check 表示记录有效，可能仍有 partial、failed 或 stale。finish 仅在所有任务为 implemented 时通过，scope 为 code-implementation。

本工具不修改 test-cases.json/html，也不把 task-plan 中的动态验收命令写成 passed。实现阶段如更新任务状态，只更新为 implemented 并重建计划 Markdown，不能据此改动用例状态。
