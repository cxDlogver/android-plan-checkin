---
name: code-execution
description: 根据 task-plan 实现代码，按任务依赖推进或安排互不冲突的并行工作，运行类型检查、lint 等静态检查并交接实现记录。用于实施或修复计划内代码；不编写或执行 Test Case 验收，不将静态检查通过写成用例通过。
---

# 代码执行

## 1. 输入与阶段边界

读取 task-plan.json、仓库指令、实际代码和计划引用的原始资料。Test Case、原子需求与 UI 结构用于理解目标与边界，本阶段不执行其中的验收步骤，不修改 test-cases.json/html 的验收状态。

本阶段交付计划范围内的实现代码和静态检查记录。单个任务完成表示：实现已覆盖该任务的 done，修改文件符合 files 范围，适用静态检查通过。它不表示需求或 Test Case 已通过验收。

## 2. 按 task-plan 实现

1. 核对任务依赖、文件范围、完成条件和现有命令。将类型检查、lint、格式校验和其他不执行产品行为的静态分析识别为本阶段检查；将测试断言、产品交互、截图和数据结果验证交给验收阶段。
2. 选择前置任务已完成实现及静态检查的就绪任务。不要要求前置任务先通过 Test Case 才开始后续实现，也不要以验收未完成为由建立实现依赖环。
3. 按计划修改代码，逐项记录 done 的具体实现位置和完成情况。范围扩大或需求语义变化时，先调整相应规划；日常实现选择在已授权范围内自行决定。
4. 使用仓库实际配置的静态命令检查当前实现。关闭自动修复等写入选项；命令隐含执行测试或交互时拆出纯静态入口。没有某类工具时记录不适用理由，不额外安装测试设施来补数量。
5. 保存实际命令、运行目录、起止时点、退出码、输出及被检查文件摘要；检查失败先修复再重跑受影响检查。全部适用静态检查通过后，才完成当前任务并允许依赖任务进入。

一个静态命令可以覆盖多个任务，记录实际范围，不要求一任务一脚本。文件冲突、前置关系和资源隔离见[实现与静态检查](references/execution.md)。

## 3. 记录与交接

使用 [implementation.schema.json](assets/implementation.schema.json)记录实现与静态检查，默认保存为 plan/code-execution/implementation.json；已有统一位置时沿用。实际源文件、检查命令配置与锁文件应能定位到当时版本。已有记录恢复使用，不重新初始化覆盖。

使用 [implementation.py](scripts/implementation.py)检查记录、判断就绪任务和阶段完成情况。工具核对范围、依赖、证据和摘要；它不判断实现是否符合需求语义，不运行 Test Case，也不写用例状态。

~~~text
python -B <skill-dir>/scripts/implementation.py init <record> --workspace <root> --plan <task-plan.json>
python -B <skill-dir>/scripts/implementation.py ready <record> --workspace <root>
python -B <skill-dir>/scripts/implementation.py check <record> --workspace <root>
python -B <skill-dir>/scripts/implementation.py finish <record> --workspace <root>
~~~

字段与状态见[实现记录契约](references/evidence-and-status.md)。交接给[验收 Skill](../acceptance/SKILL.md)时提供 task-plan、实现记录和当前源码版本，由验收阶段根据 Test Case 路径规划实际执行。

## 4. 审查与结束

核对实现范围、依赖顺序、done 对应代码，以及静态检查是否真实执行、证据是否适用于当前文件。check 只报告记录有效性；finish 要求所有任务的实现及静态检查完成。

最终保留实现代码、implementation.json 和必要静态检查输出。task-plan 的任务状态可登记为 implemented；不得登记为需求验收 passed。Test Case 状态由验收 Skill 管理。

完成后删除本任务创建的草稿、探索脚本和中间报告，保留可复现检查的正式配置与证据。向用户说明“代码实现及静态检查完成，待验收”；只请求代码执行时到此结束。
