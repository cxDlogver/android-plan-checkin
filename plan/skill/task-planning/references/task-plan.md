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
| checks | 将来执行的命令/人工方法，声明requires前置任务；规划中status=not_run |
| status | 规划固定planned |

每个用例至少有任务负责。每个任务的requirementIds恰等于testCaseIds映射到的非空requirementId集合。共享基础任务可映射多用例；不得仅因依赖某公共任务而无限扩大它的代码修改范围。

任务检查描述未来动作，规划阶段不写成已完成测试。当前不存在的测试脚本注明由哪个前置任务建立；不要把计划命令包装成已经可运行的命令。

## 3. 直接影响

impacts包含id、behavior、codeEvidenceIds、changedFiles、mechanism、exposure、decision、testCaseIds、reason。

decision=regression时，明确原有行为、拟修改边界导致损害的机制、能触发差异的输入，且至少映射一个regression用例。decision=covered时由已有主用例充分覆盖并映射它；decision=unaffected时说明边界为何保留，用例为空。没有读取依据或具体因果链的潜在影响不冒充已确认回归责任。

例如修改按钮公共实现可能破坏disabled拦截和onPress透传，应安排脚本验收，在真实控件宿主中分别检查禁用点击与启用点击；只改变按钮颜色且保留Pressable事件实现时，依据差异检查可以判定事件行为未受直接影响。数据库仅被页面读取而无存储代码和命令协议改动时，不因此把所有迁移测试纳入回归。

## 4. 执行前置项

prerequisites记录id、description、status、affects、resolution和source。status为ready或missing；affects定位用例，resolution说明补足标准。source使用原文档文件或已登记代码证据的直接位置，不能用临时问题ID替代。

缺少资源、宿主或测试工具时，保持用例not_run并标出阻碍。不因资源缺失推迟能够确定的任务拆分，也不擅自替换需求指定字体、删减验收项或创建实际用户授权。

## 5. 产物与审查

task-plan.json是任务数据源，task-plan.md由同一脚本生成可读视图，包含输入版本、路线计数、前置项、代码证据、影响判断与逐任务范围/映射/检查。验收图侧栏只展示可读验收步骤、类型、证据及状态；文件范围和用例/需求映射由任务计划保存，不在侧栏重复展示。

脚本检查文件存在与哈希、定位片段、修改证据、依赖无环、映射闭合及数据同步。审查者仍需核对步骤是否足以实现需求、实际风险是否遗漏及验收方法是否充分。终态被Mock直接提供、无观察方法、随意标独立入口等问题即使JSON结构有效也不能通过语义审查。

## 5. 实施后的状态

任务实施和脚本验收由[代码执行规范](../../code-execution/SKILL.md)负责。任务 status 与 checks.status 根据本任务完成标准及实际局部脚本结果同步；映射到同一用例的多个任务不要求相互等待完整用例验收。规划时应为基础任务提供可独立验收的局部检查，后续任务承担整合后的完整用例检查，避免检查前置关系形成执行环。原始 codeEvidence 保留实施前摘要，实际运行版本写入执行证据。
