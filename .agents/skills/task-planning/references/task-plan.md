# 代码分析与任务计划

## 1. 实际链路证据

从需求对应的入口读取组件、事件处理、状态和依赖边界，登记codeEvidence：id、path、原始文件sha256、locator、excerpt、role。locator采用实际L起止行；excerpt必须存在于该范围。先读后写，不用文件名或历史报告推测职责。

每个任务files列出path、change、purpose、evidenceIds。已有源文件使用modify并引用同文件读取证据；新文件使用create且不能已有同名文件。read只表示实现时需参考的依赖，不增加修改授权或回归责任。所有路径相对task-plan.json解析并限制在workspace。

## 2. 任务字段

根包含schemaVersion、title、revision、testCases、codeEvidence、impacts、prerequisites、tasks。testCases绑定本版test-cases.json内容摘要。

| 任务字段 | 要求 |
| --- | --- |
| id/title | 稳定身份和具体交付结果 |
| goal | 修改什么并获得哪个可观察结果 |
| dependsOn | 同文件任务ID；依赖构成DAG |
| files | 实际文件级范围及modify/create/read责任，不使用目录通配符替代 |
| steps | 具体改动及挂载方式；不把“完成页面”“实现所有逻辑”作为唯一说明 |
| testCaseIds | 本任务负责支撑或实现的用例 |
| requirementIds | 本任务用例对应的主原子需求集合；补充用例不编造新需求 |
| done | 可判定的完成条件 |
| checks | 代码实现阶段适用的类型、lint等静态检查命令，声明requires前置任务；规划中status=not_run。Test Case行为验收保留在用例定义中 |
| status | 规划固定planned |

每个用例至少有任务负责。每个任务的requirementIds恰等于testCaseIds映射到的非空requirementId集合。共享基础任务可映射多用例；不得仅因依赖某公共任务而无限扩大它的代码修改范围。

任务检查描述未来动作，规划阶段不写成已完成测试。当前不存在的测试脚本注明由哪个前置任务建立；不要把计划命令包装成已经可运行的命令。

## 3. 直接影响

impacts包含id、behavior、codeEvidenceIds、changedFiles、mechanism、exposure、decision、testCaseIds、reason。

decision=regression时，明确原有行为、拟修改边界导致损害的机制、能触发差异的输入，且至少映射一个regression用例。decision=covered时由已有主用例充分覆盖并映射它；decision=unaffected时说明边界为何保留，用例为空。没有读取依据或具体因果链的潜在影响不冒充已确认回归责任。

例如修改按钮公共实现可能破坏disabled拦截和onPress透传，应安排脚本验收，在真实控件宿主中分别检查禁用点击与启用点击；只改变按钮颜色且保留Pressable事件实现时，依据差异检查可以判定事件行为未受直接影响。数据库仅被页面读取而无存储代码和命令协议改动时，不因此把所有迁移测试纳入回归。

## 4. 执行前置项

prerequisites记录id、description、status、affects、resolution和source。description/resolution写明可执行准备动作、可观察的就绪条件及必要证据；status只表示规划时的基线，验收通过实际准备核对，不能把尚未启动宿主或尚未生成验收合同视为不能进入验收准备。status为ready或missing；affects定位用例，resolution说明补足标准。source使用原文档文件或已登记代码证据的直接位置，不能用临时问题ID替代。

缺少资源、宿主或测试工具时，保持用例not_run并标出阻碍。不因资源缺失推迟能够确定的任务拆分，也不擅自替换需求指定字体、删减验收项或创建实际用户授权。

## 5. 产物与审查

task-plan.json是任务数据源，task-plan.md由同一脚本生成可读视图，包含输入版本、路线计数、前置项、代码证据、影响判断与逐任务范围/映射/检查。验收图侧栏只展示可读验收步骤、类型、证据及状态；文件范围和用例/需求映射由任务计划保存，不在侧栏重复展示。

脚本检查文件存在与哈希、定位片段、修改证据、依赖无环、映射闭合及数据同步。审查者仍需核对步骤是否足以实现需求、实际风险是否遗漏及验收方法是否充分。终态被Mock直接提供、无观察方法、随意标独立入口等问题即使JSON结构有效也不能通过语义审查。

## 6. 实施与验收的交接

[代码执行](../../code-execution/SKILL.md)负责按任务依赖实现代码并完成类型、lint 等静态检查；实现完成记录为 implemented，不等待 Test Case 通过。task-plan 的静态检查与 Test Case 的动态验收分别规划，不能以动态验收阻塞实现依赖。

[验收](../../acceptance/SKILL.md)在实现交接后，先通过只读 preflight 进入准备阶段，再复制 test-cases.json/html 与 task-plan.json/md 到验收目录；原规划产物保持只读。验收依据副本的 coverage.sequence 规划会话并逐项执行，每次访问只在副本、合同及验收记录中登记证据、更新状态并核对后推进。Test Case 的最终 passed 表示全部必要检查和访问完成；静态检查通过不产生该结论。原始 codeEvidence 保留实施前摘要，两个阶段分别记录实际检查版本。
