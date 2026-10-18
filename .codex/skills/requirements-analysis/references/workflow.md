# 初始化、过程目录与交付产物

产物位置由用途决定：供后续阶段直接消费或供人工审查的产物放在输出根目录；本阶段的工作模型、来源缓存、内部评审、待办、诊断及临时文件全部放在唯一的 _process/ 子目录中。不得因为文件已经生成，就将其列为根目录交付物。

## 放置规则

- 根目录文件必须具有明确的后续消费者或人工审阅用途，且内容足以独立理解其作用。
- 只服务本阶段推导、校验、生成和继续执行的文件放入 _process/；可在其中按用途分组，但根目录不再另建 evidence/、review/、logs/ 等过程目录。
- 根目录可以展示待确认草案，其阶段、待决项与验收状态必须真实；“已导出”不等于“已接受”。
- 新增文件先判断用途。没有下游消费或人工审查用途的，一律归入 _process/。临时脚本、工具输出、自测结果不自动成为规范产物。
- 同一任务持续维护相同路径，不保存进度快照、历史模型或按轮次复制目录，不强制递增版本号。

## 从需求分析职责推导布局

RUN 是用户指定的输出目录，未指定时为 plans/<analysis-name>；WORK = RUN/_process。S 为本 Skill 目录。

~~~text
RUN/
├─ state-graph.json             后续消费：状态、事件、守卫、迁移及逐边可执行见证
├─ atomic-requirements.json     后续消费：每条原子需求的完整结构与验收约束
├─ requirement-graph.json       后续消费：原子需求的连续覆盖路线、次数与实际用边
├─ analysis-model.json          后续消费：完整分析模型的生成结果
├─ review-log.json              人工审查：循环补漏、待决项与决定
├─ review.html                 人工审查：双图、需求详情、链路与 UI 对照
├─ manifest.json               后续消费：交付文件清单与内容一致性校验
├─ gate-result.json             人工及后续阶段：当前内容是否满足交付门禁
├─ acceptance.json              人工及后续阶段：最终真实确认及其覆盖内容
└─ _process/                   本阶段全部中间分析产物
   ├─ analysis-model.json       唯一可编辑工作模型
   ├─ run-state.json            当前阶段、待审节点、待决项与下一步
   ├─ gate-contract.json        本次固定检查项与执行状态
   ├─ model-review.json         独立模型内部评审报告与待修问题
   └─ evidence/                资料缓存、UI 图片、真实答复与评审观察
~~~

这是一份覆盖完整流程的产物计划，不表示初始化就创建全部文件。源数据、问题、人工决定和循环记录统一维护在 WORK/analysis-model.json；根目录 analysis-model.json 是同源导出，提供后续阶段完整的语义输入，不再作为第二个编辑源。HTML 内嵌 UI 媒体，不单独输出根目录媒体缓存文件。人工界面仅展示中文图结构及点击后的链路／效果，不展示工作模型的 JSON 字段；状态 Canvas 保留全部业务迁移，需求 Canvas 只显示覆盖路线用边并保留全部需求节点，兼容一个或多个顶层 entryStateIds 真实起点；点击状态的链路保留必要上下文并止于所选状态，点击箭头打开对应需求。视觉区将UI图与来源明确的CSS设计值并列。详见 html-review.md。

## 创建时机与持续维护

| 产物 | 创建时机 | 更新责任与用途 |
| --- | --- | --- |
| WORK/analysis-model.json | init 创建空草案 | 每完成资料读取、迁移组、问题处置或节点审查，立即更新范围、来源、状态、需求、UI 和审查记录 |
| WORK/run-state.json | init 创建当前信息 | AI 写活动节点、等待原因和 next_action；save 重算摘要及当前待审/待决清单 |
| WORK/gate-contract.json | init 从固定模板创建，检查全部 pending | save 使旧检查失效；assert 重算当前条件，不保留历史合同副本 |
| WORK/evidence/ | init 创建目录 | 实际读取资料或收到答复后保存证据、定位和摘要；文件存在不等于已读 |
| 根目录双图、原子需求、完整模型、review-log、HTML、manifest | 模型结构合法后 prepare 生成 | 从同一工作模型在根目录整体更新；下游与人工从这些入口消费，禁止单独手改导出内容 |
| WORK/model-review.json | 独立评审实际发生时 | 按固定 rubric 记录语义结论和待修问题，绑定当前模型与根目录交付摘要 |
| RUN/gate-result.json | assert 实际执行时 | 提供当前门禁状态及失败原因；save 删除旧结果，等待重新检查 |
| RUN/acceptance.json | 真实最终整体确认后 | 保存回复引用和所确认的内容/交付/报告摘要；修改后不能自行刷新摘要沿用旧同意 |

初始化仅创建 _process/ 内的工作模型、当前状态、门禁合同和 evidence/，根目录不放空交付文件或虚构验收结论。后续过程中新产生的笔记、诊断、临时生成目录仍须在 _process/ 内，完成后清理不再需要的临时文件。

## 初始化与增量维护

Python 3.10+，仅标准库。所有命令均传入 RUN，脚本自行定位 _process/。

~~~text
python S/scripts/workflow.py init RUN --run-id <task-id> --context <真实分析上下文ID>
python S/scripts/workflow.py save RUN
python S/scripts/workflow.py resume RUN
~~~

init 接受不存在或空目录；已有任务读取工作模型继续。补入初始范围后再 save。每完成一个有意义的小单元，就写入当前工作模型与证据并 save，不能只留在对话中。先保存真实答复，再依据它调整需求。

run-state 字段为 run_id、phase、round_id、active_node_id、pending_node_ids、open_question_ids、semantic_digest、waiting_for_user、pause_reason、next_action。它仅保存当前信息；不记录历史模型和完成步骤快照。

每轮审查开始即绑定当前 modelDigest，逐节点保存 checks。十维检查齐全才从待审集合移出；含义改变后重新全量审查，不能替换摘要将旧检查冒充新检查。resume 校验当前工作文件与证据，返回下一步，不回退历史内容。

## 生成根目录交付

~~~text
python S/scripts/workflow.py prepare RUN
python S/scripts/workflow.py assert RUN
~~~

prepare 从 WORK/analysis-model.json 重新计算逐边可执行见证并生成完整状态图、需求覆盖图、全部原子需求以及每个真实起点到每个状态的到达结果，并内嵌到 HTML；不沿用上次所选节点的缓存链路，也不只更新当前功能分组。UI 或模板变化同样重新生成。全部临时生成文件先写在 _process/ 内，完成校验后替换同名根目录产物，manifest 最后写入；临时目录结束即清理。若路径搜索、生成或写入未完成，报告失败／未完成；旧产物即使仍存在，也不得作为当前修改完成的证据。assert 拒绝与当前输入不一致的结果，修复当前文件后重新 prepare。

manifest 只列出根目录同源生成的分析交付，不把工作状态、缓存和临时文件混入交付摘要。gate-result 与 acceptance 分别依据实际检查和人工作答生成，避免循环计算摘要。根目录出现未声明的中间文件或其他子目录时，脚本拒绝继续，先按用途整理，不自动删除用户文件。

所有 evidencePath、previewPath、评审 evidence_refs 和最终回复 evidence_path 都是相对 RUN 的路径，指向 _process/evidence/。HTML 内嵌图片；JSON 保留来源 URI、定位及证据引用。整体目录保留这些追溯依据，后续阶段默认从根目录正式产物读取。

## 独立模型评审

用独立子代理/会话读取当前分析、PRD/UI、已确认范围、循环记录、根目录交付及固定 rubric；不给预设通过答案。上下文 ID 须不同于分析者。评审结果写 WORK/model-review.json；缺少独立环境如实记录未完成。

报告字段：review_id、reviewer_context_ref、independent、semantic_digest、bundle_digest、reviewed_entity_ids、input_complete、criteria_results、evidence_files、findings、limitations、html_runtime_verified；当前模型含自环时必须有 self_loop_reviews[]。

self_loop_reviews 每项含 transition_id、status、reason、evidence_refs。必须逐条覆盖当前全部自环且不重复、不混入其他迁移；status 使用 pending/passed/failed/inconclusive。原因须核对精确来源支持、独立义务与同一状态理由；证据也纳入 evidence_files 的摘要校验。缺条目、失败或未决不能被 branch_meaning 的笼统 passed 覆盖。无自环时该列表为空。

criteria_results 恰含固定八项，每项有 criterion_id、status（pending/passed/failed/inconclusive）、reason、非空 affected_ids 与 evidence_refs。evidence_files 将证据路径映射到 SHA256。有开放问题、缺失输入或未实际浏览 HTML 时不能通过。模型、来源或交付变化使旧报告失效，修复后独立复审，更新同一文件。

## 最终人工确认

assert 返回 awaiting_final_confirmation 后，展示根目录 HTML、当前结论和待决处置，请用户整体确认。真实回复保存到 WORK/evidence/，生成 RUN/acceptance.json：

~~~json
{
  "semantic_digest":"当前语义摘要","bundle_digest":"根目录交付摘要",
  "review_digest":"_process/model-review.json文件SHA256","covered_ids":["S1","T1","R1"],
  "human_reference":"真实对话引用","summary":"用户明确确认内容",
  "evidence_path":"_process/evidence/final-reply.md","evidence_sha256":"真实回复缓存SHA256"
}
~~~

~~~text
python S/scripts/workflow.py assert RUN
python S/scripts/workflow.py publish RUN
~~~

publish 重查同一套根目录产物，全部 passed 才成功，不创建另一个发布目录。根目录模型可以保留评审阶段的 draft/review_ready；正式接受以内容摘要匹配的 acceptance 与 gate-result 为准。修改内容后回到工作模型修订、重审和重新导出；不得直接编辑根目录结果绕过一致性检查。程序不能认证人工作答或独立上下文的真实性，执行 AI 必须核对实际会话。
