# 运行、增量保存与恢复

Python 3.10+，仅标准库。S 为 skill 目录，RUN 为本次独立输出目录（未指定时 plans/<analysis-name>）。有空格的路径按所用 shell 加引号。失败非零退出；assert 的 passed 与 awaiting_final_confirmation 返回 0，只有 passed 能 publish。

## 初始化与事实源

```text
python S/scripts/workflow.py init RUN --run-id <task-id> --context <真实构建上下文ID>
python S/scripts/workflow.py resume RUN
```

init 只接受新目录，复制固定 assets/gate-contract.json；所有检查 pending、证据空。创建 evidence/、checkpoints/、current.json，以及可编辑的 analysis-model.json、run-state.json。初始空模型是待填草案，不是通过证据。

模型记录已知需求；run-state 记录做到哪；合同记录必须满足的检查。current.json 指向经 manifest 校验的完整检查点，是恢复权威。根目录模型和状态是方便编辑的工作副本，直接改它们不代表已提交。历史用于恢复与核对过程，不要求事件重放数据库。

run-state 字段：run_id、phase、round_id、active_node_id、pending_node_ids、completed_step_ids、open_question_ids、artifact_revision、semantic_digest、last_checkpoint_ref、waiting_for_user、pause_reason、next_action。脚本计算版本／摘要／队列／完成步骤等派生字段；AI 填活动节点、轮次、等待、暂停原因、下一步。语义变更后全量加入待审，闭合审查逐节点移出，不依赖 AI 仅填“已完成”。

## 小单元完成立即提交

编辑工作副本，本单元完成后、下一单元开始前写 step.json 并执行：

```text
python S/scripts/workflow.py checkpoint RUN --model RUN/analysis-model.json --state RUN/run-state.json --record <step.json> --base <resume返回的checkpoint>
```

step.json：

```json
{"id":"read-prd-01","kind":"source","entityIds":["SRC-01"],"evidenceRefs":["evidence/prd-01.md"],"summary":"读取输入规则一节；保存观察与未定义项"}
```

id 本运行唯一。kind：source、model、question、node_audit、round、decision、pause。entityIds 解析到当前模型 ID（或 scope）；evidenceRefs 是相对 RUN、不可越界的缓存文件路径；source 和 decision 单元必须有证据。节点审查每次只保存一个完成节点，另填 roundId。summary 描述本单元事实。已读观察可直接写缓存 Markdown，不得只保存在聊天里。

| 完成单元 | 当次保存 |
| --- | --- |
| 一个资料片段／画板 | source（读取范围、版本、证据摘要）、缓存与观察；source 单元关联来源 ID |
| 一组能独立说明的迁移 | 同步状态、迁移、需求、UI、来源；model 单元 |
| 未定义规则／冲突 | questions、候选与双向 affectedIds/questionIds；question 单元 |
| 一个节点的十维检查 | round.checks 的证据和理由、新前沿；node_audit，entityIds 仅该节点 |
| 一轮／有效含义变化 | 轮次、revision、变化和新队列；round 或 model 单元 |
| 人工回答 | 原文缓存、人类来源和决定；decision 单元，先落盘再依赖它修改模型 |
| 暂停／压缩／切换上下文 | pause，明确 pause_reason、next_action 和未完前沿 |

node_audit 不能同时改模型含义；先保存修改与新 revision，再审节点。所有 node_audit 须绑定当前语义摘要与闭合轮。新增轮即使未改需求，也要重新保存该轮逐节点过程。十维完成不等于语义完备，理由由独立评审核对。

checkpoint 将模型、状态、本步记录写入新目录，校验后原子切换 current.json；中断的未指向目录不算完成。--base 不匹配拒绝旧快照覆盖，独占锁防止正常入口同时提交。异常遗留 checkpoint.lock 时先确认没有写入进程、保存诊断后显式删除锁，不自动猜测失效。

## 恢复

```text
python S/scripts/workflow.py resume RUN --restore
```

验证合同、指针、已提交历史、每个文件和证据摘要、完成步骤清单、版本与状态一致性，成功才恢复工作副本并返回下一步。restore 会覆盖未提交副本，先保存有价值的未完工作供补做。丢失／不一致时失败，保留原物并定位最近完整检查点。指针损坏的灾难恢复须显式检查 manifest 后修复指针；正常 resume 不自动退回旧版本冒充最新。

## 准备快照与独立验收

```text
python S/scripts/workflow.py prepare RUN <新的review-bundle目录>
python S/scripts/workflow.py assert RUN --bundle <review-bundle> --review <model-review.json>
```

prepare 可导出合法的分析中草案；review_ready 必须已有当前版本闭合审查，不能空 rounds。只接受新目录，失败保留未发布 staging 供诊断。每包 manifest 记录文件集、SHA256 和 bundle_digest，不得手改后沿用旧摘要。原始缓存保留在 RUN/evidence，UI 可预览图片嵌入 HTML 和 ui-media.json。正式交付保留 RUN 以回溯原稿。

独立评审用新子代理／独立会话，给真实模型、原始 PRD/UI 证据、初始范围、审查记录、完整导出包和固定 rubric，不给预设“应当通过”的答案。记录真实上下文 ID，不同于 init --context。环境没有独立上下文就记录未完成，不能把改写自评叫独立验收。

model-review.json：

```json
{
  "review_id":"review-01","reviewer_context_ref":"实际独立上下文ID","independent":true,
  "reviewed_revision":"r8","semantic_digest":"model_tools digest结果",
  "bundle_digest":"已审包manifest中的bundle_digest",
  "reviewed_entity_ids":["S1","T1","R1"],"input_complete":true,
  "criteria_results":[{"criterion_id":"source_consistency","status":"passed","reason":"具体对象与核对结果","affected_ids":["R1"],"evidence_refs":["evidence/reviewer-observations.md"]}],
  "evidence_files":{"evidence/reviewer-observations.md":"该文件SHA256"},
  "findings":[],"limitations":[],"html_runtime_verified":true
}
```

示例仅演示一项，实际覆盖固定八项，每项一次。status=pending/passed/failed/inconclusive。每项需具体理由、非空当前实体引用、证据路径；evidence_files 索引证据 SHA256。findings 每项含 id、status（open/resolved）、说明和对象，有开放发现不得 passed。input_complete=false、报告缺失、HTML 未实际浏览均未完成。HTML 观察记录真实工具／浏览器上下文、步骤、统计对比与结果，附可用截图。脚本只核对声明和证据一致性，语义由独立评审负责。

报告或包改变须重新 assert；语义或证据改变，重审后刷新报告；不能手填 passed 冒充执行。最终待决先问人，答案导致语义变化则修复、全量闭合和独立复审，再请求整体确认。

## 最终确认与发布

assert 返回 awaiting_final_confirmation 后，在对话展示版本、双图 HTML、待决处置和验收结果，请用户整体确认。保存真实回复，建立 acceptance.json：

```json
{
  "revision":"r8","semantic_digest":"当前语义摘要","bundle_digest":"已审包摘要",
  "review_digest":"model-review.json文件SHA256","covered_ids":["S1","T1","R1"],
  "human_reference":"真实对话消息引用","summary":"用户明确确认内容",
  "evidence_path":"evidence/final-reply.md","evidence_sha256":"回复缓存SHA256"
}
```

```text
python S/scripts/workflow.py assert RUN --bundle <bundle> --review <report> --approval <acceptance.json>
python S/scripts/workflow.py publish RUN <新交付目录> --bundle <bundle> --review <report> --approval <acceptance.json>
```

评审快照不因最终回复改写；发布包另加 acceptance.json、model-review.json、gate-result.json，重封 manifest。HTML 中 draft/phase 是当时快照，正式确认以同包 acceptance 与 passed gate 为准。后续改需求需新版本、新包、新确认。最终回复先缓存并记录 decision 检查点（模型与 phase 保持已审内容），再 publish。

确认真实性由执行 AI 核对实际人工作答；程序不能认证。正常入口门禁不提供文件权限隔离，未配置运行时 Hook。
