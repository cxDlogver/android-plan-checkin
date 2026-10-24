---
name: task-planning
description: 将已澄清的原子需求转为 Test Case 验收有向图和代码实现计划，默认单元测试与集成测试、记录预期和实际观察，校验验收进入顺序、最少重复遍历、覆盖及完整产物。用于任务规划，不自动实现应用或宣称测试已通过。
---

# 任务规划

本规范不内置产品、业务实体、框架或项目路径。输出项目中的 task-planning/，Skill 本身与示例分开保存。

## 1. 读取规划输入

读取当前 PRD、澄清结论和原子需求，登记需求模型与上游门禁文件的路径、SHA256 及语义摘要。检查来源版本和未决项；未完成澄清不能用假定答案生成正式计划。默认复用已确认的业务含义，不重复询问已回答的问题。没有代码时如实登记基线；已有代码按职责和差距规划，不将现有行为反推为需求。

结构参考 [规划契约](references/model-contract.md) 和 [Schema](references/planning.schema.json)。输入为通用需求模型：atomicRequirements、nonTransitionRequirements、states、transitions、scope；字段映射不同的来源时先显式转换并保留原始来源，不静默丢项。

## 2. 构建 Test Case 有向图

默认每条原子需求恰好一项 primary Test Case。多个共同断言或输入样本可在同一用例内组织；确有跨需求集成价值时，额外登记 scenario 用例与多对多映射理由。交付物、质量等非迁移要求另建 supporting 用例，不伪装为原子业务需求。

每项包含：来源需求、单元/集成层级、独立数据夹具、验收步骤、明确预期期望、观测方法、实际观察记录、证据、测试文件/命令计划。每条功能验收标准和视觉标准均通过 criterionRefs 映射到预期断言；不可自动验证的视觉细节记录局限，不能以类名或快照宣称真实布局正确。

默认不使用浏览器：单元测试检查领域逻辑，集成测试检查模块、存储、模拟 DOM 或本地 HTTP。没有用户授权不启动浏览器、录屏或截图流程。DOM 模拟与 CSS 契约可以验证部分 UI 语义，不证明真实排版、遮挡或像素效果。

图边只表示验收顺序，不直接复制需求状态衔接图，也不代表开发依赖。每个非起始用例只能从本次运行中刚通过的上一个用例沿显式边进入；不能依靠旧运行的 pass、跳过失败、从孤立用例直接标记验收通过。起始用例无前序用例和外部业务前置条件，所需数据/环境初始化在自身验收步骤中显式执行。

优先使用用例自有隔离夹具，准备与清理都是可审阅步骤，不复跑其他 Test Case 造数据；顺序门禁仍独立生效。需要共享业务上下文的集成链放在一个 scenario 用例内，或明确声明 carry 模式及状态交接；不能用夹具重置伪造共享链验证。

先明确哪些先后关系真实必要，再选覆盖所有节点的遍历路线。隔离用例可采用单次串行路径：N 个节点各一次、N−1 条边，重复访问为 0，达到至少访问 N 个节点的下界。若受共享状态或既定边约束无法做到，记录重复原因与优化方法；无最优性证明时写 heuristic，不宣称全局最优。重试不属于规划的无失败基准路线；实际重试须留痕。

实际观察在尚未执行时为 not_run、观测值/证据为空。预期不得复制成实际结果。执行时每次访问记录运行 ID、实现版本、模型摘要、实际值、逐断言结果、命令、退出码及证据文件哈希；前序失败后停止，不计为后续通过。模型或实现版本改变应开新运行。

## 3. 代码实现计划

生成 plan.json 和 plan.md，写明基线、架构/选型理由、模块与文件职责、实现步骤、任务依赖、需求/用例映射、输出、完成标准和计划命令。技术栈依当前项目选择，不固化进通用 Skill。区分开发任务依赖 DAG 与 Test Case 验收顺序。

安排测试夹具和验收调度器，使真实执行能遵守图；调度器是实现计划中的交付，不因有图文件就宣称已实现。版本选择需匹配已核验的本机环境并生成锁文件。所有步骤仍是 planned，除非有实际工作证据；规划不隐含开发、上传或交卷授权。

## 4. 门禁与产物

按 [门禁规范](references/gates.md) 做语义审查；以 planning-model.json 为唯一编辑源。运行：

~~~text
python <skill-dir>/scripts/plan_tools.py render <planning-model.json>
python <skill-dir>/scripts/plan_tools.py digest <planning-model.json>
python <skill-dir>/scripts/plan_tools.py gate <planning-model.json>
python <skill-dir>/scripts/plan_tools.py next <planning-model.json>
~~~

语义审查绑定 reviewDigest 后再 render/gate。next 校验当前运行轨迹，给出唯一基准路线的下一项；无有效 pass 不越过前序。工具核验结构、来源、覆盖、顺序、观察记录和派生一致性，不替代实际测试执行。

输出：planning-model.json；test-cases.json/md；test-case-graph.json/md（含路线与重复下界证明）；plan.json/md；execution-record.json/md；gate-report.json/md。

门禁区分 planningStatus 与 executionStatus：计划可完整通过，而应用测试仍全部 not_run。交付时明确该区别以及无浏览器验证的剩余边界。
