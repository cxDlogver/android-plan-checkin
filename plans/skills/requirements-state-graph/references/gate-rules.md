# 固定验收门禁

固定规则和 rubric 是 assets/gate-contract.json。不得按本轮难易删规则或补造通过记录。init 全 pending；assert 重算实际检查，旧 checks 的 passed 不作依据。失败含 rule_id、failed_object、expected、actual、evidence_ref、failure_reason、repair_from、recheck_from。

## 机械规则

下表适用于最终整体确认／发布。prepare 草案只检查基本结构，可供集中澄清，但不代表通过。修复后重跑该项及依赖门禁。

| ID / 类型 | 通过条件与必需证据 | 修复／重查起点 |
| --- | --- | --- |
| INIT-001 / 程序 | 合同版本、模板摘要、完整规则集与初始检查点正确 | 固定模板初始化或显式迁移，保留旧运行 |
| SOURCE-001 / 程序 | 每来源版本、读取范围、真实缓存、SHA256、可选图片预览摘要匹配 | 补读资料、保存证据，再查来源与语义 |
| SCOPE-001 / 程序＋人 | 真实初始确认绑定当前 scopeDigest；相同范围可跨 revision | 人工确认新范围、保存决定，再分析 |
| MODEL-001 / 程序 | schemaVersion=2，结构、类型、枚举、来源／UI／功能引用合法 | 修模型、全量验证 |
| LINK-001 / 程序 | 迁移需求双向一一对应，衔接公式成立，边 ID 无歧义且唯一 | 修迁移／需求，同源重导出 |
| PROCESS-001 / 程序 | 指针历史可校验，来源及当前每节点审查有已提交单元，待审队列空 | 恢复完整点，执行缺失单元，不补造历史 |
| AUDIT-001 / 程序 | 至少一次建模／审查后，当前摘要闭合轮覆盖全状态×十维，无变化／前沿；phase=review_ready 或 confirmed | 从缺节点、轮次或变更后重审 |
| QUESTION-001 / 程序＋人 | 所有开放问题处置、候选转有据草案；affectedIds/questionIds 一致 | 最终集中问答、修订、闭合与评审 |
| MODEL-REVIEW-001 / 程序消费LLM | 真实独立上下文、完整输入、当前语义／包摘要、实体全覆盖、八项 passed、证据可校验、无开放发现 | 修复并独立复审；缺证补证重审 |
| ARTIFACT-001 / 程序 | 当前模型、导出、HTML、图片与 manifest 完整同包，逐份对账 | 当前检查点重新 prepare 到新目录 |
| APPROVAL-001 / 程序＋人 | 真实最终回复，语义／包／报告摘要和全部实体覆盖一致 | 双层通过后取得当前版本整体确认 |

程序核对报告结构、声明、对象和证据一致性，不替代模型的语义判断。人工作答和独立性真实性由执行 AI 核对实际会话，程序不能认证。

## 独立模型 rubric

| criterion_id | 开放性验收 |
| --- | --- |
| source_consistency | 原文、范围、需求事实一致；附件指令未升级为要求 |
| branch_meaning | 新分支改变义务，等价排除有理由，未臆造异常业务 |
| atomicity | 一迁移为独立行为；结果和共同断言完整 |
| guards_and_complements | 条件、合法域、反面与边界有据，未知未补默认值 |
| ui_mapping | 实际画板／区域／状态对应，缺稿与无UI区分 |
| unresolved_decisions | 未定义未隐含选定；人工决定与影响相符 |
| convergence | 最后变更后全量复审，新／受影响节点处置充分；限定范围 |
| html_observation | 实际浏览双图、环／平行边、多连通部分、搜索筛选、详情／链路、UI／缺稿；统计版本一致，有观察证据 |

报告绑定精确包摘要，HTML 变化也使报告过期。failed 修复重审；inconclusive、输入截断、无独立上下文或 HTML 未运行不能通过。最终待决澄清可以发生，但双层通过前不请求整体验收。

## 计算结果

- 机械规则或模型报告有确定失败：failed，模型通过不能覆盖。
- 必需检查／报告／证据未完成：pending。
- 除 APPROVAL-001 外全 passed：awaiting_final_confirmation，才允许请求整体确认。
- 全 passed：passed，publish 才能整包发布。

输出存在不等于通过；assert 不是运行时 Hook，不能防止绕过命令直接改文件。不要配置全局 Hook 或声称权限级强制。
