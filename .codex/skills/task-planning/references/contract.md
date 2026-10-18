# 产物与确定性合同

```text
<output>/
  test-plan.json             后续唯一结构化输入：测试项、原状态/需求图、映射测试图、继承路线、任务、证据槽和输入绑定
  test-cases.md              准备、步骤、预期、判定及连续验收顺序
  implementation-plan.md     开发顺序、复用/修改位置、依赖、完成条件、必要检查和风险
  review.html               人工只读 Canvas 审查入口
  gate-result.json           当前检查、资料就绪与验收状态，避免草案被误认通过
  _process/                 本阶段全部中间工作（唯一子目录）
    planning.json            当前工作数据；初始化后按功能/影响链持续维护
    export-index.json        当前导出文件摘要，build 后创建，用于拒绝过期或手改派生产物
    review.json              独立评审，发生时创建
    approval.json            最终真实人工作答，发生时创建
    evidence/                必需调查/检查/实测证据，发生时创建
```

初始化只创建工作模型、声明输出用途，不创建空报告、历史档案或 Skill 验证目录；Skill 作者自己的验证文件如需要放在任务的 _process/，不是每次运行的强制产物。相同路径原位更新；输入变更后先重读和重评，不能自动刷新哈希维持通过。

工作模型字段：

- inputs[]：role/path/sha256/readRanges。角色 analysisModel/stateGraph/requirements/requirementGraph/requirementsReview/prd/uiSpec/tokens/pageMap。requirementsReview 指向上游 review.html，内容与结构化输入一致。非本项目可先做等价适配，保留转换依据。
- repository：root/exists/evidence[]（相对 path、sha256、读过的 lines、finding）。不读无关凭证。
- scope：目标、排除项、initialConfirmation（真实回复）。
- issues[]：问题、依据、影响、resolution；未解决阻止正式就绪，不妨碍草案。
- tasks[]：id/title/dependsOn/codePaths/approach/doneWhen/requirementIds/regressionIds/checks/status。开发检查 kind 仅 static/unit；集成、浏览器、模拟器属于后续 acceptance。新建路径标明 planned。
- regressionPolicy：mode=deferred/included。deferred 时 regressions 和任务 regressionIds 必须为空；后续回归单列，不改变主测试图。
- regressions[]：独立测试定义和 impact（changedPaths/affectedPaths/existingContract/risk/sourceRefs/whyNotCovered）；已有主项足够就标回归用途，不新增。
- overrides：按需求 ID 提供准备数据、步骤、实例或 additionalAssertions；只追加有依据的断言，不能覆盖源断言。sharedAssertions 显式登记源断言文本到共享约束的归类与 coveredBy(caseId/assertionId) 验证归属，不硬编码某个项目的中文句子。
- uiAssets：引用图片 path/sha256；acceptanceMatrix 指定已要求环境及 bindings(environment/caseId/instanceId)，环境必须对应实例的 environment，未绑定保持草案。
- routePreparations：按路线 ID 登记 routeDigest、setup、controls、restore、sourceRefs、guardReview；摘要匹配且字段完整才标准备已定义，独立语义评审仍须检验真实可执行。改路线后旧准备失效。
- routePolicy：mode=inherit_requirement_graph；不在主图生成阶段搜索或优化。路线来自输入需求图的 traversal；结构覆盖/条件冲突/未验证逐项保留。
- results：只在 acceptance 阶段通过 record 维护；渲染不改变通过状态。

测试项包含 id/kind/requirementId/transitionId/title/featureIds/setup/steps/expectedState/assertions/uiRefs/globalConstraintIds/instances/readiness/result。assertions 有 id/kind/text/sourceRefs/applicability；至少一个 functional。visual 可以 supported/not_specified/not_applicable 并说明原因。多环境作为实例，不重复建逻辑需求。

预期在 assertions；实际在 result。result.status=pending/failed/passed；readiness=ready/blocked 单列。所有适用断言和必需实例证据齐备才可通过；任一失败则失败，其余待验收。共用录像逐断言定位片段，不共用通过结论。

```text
python -B scripts/planning.py init <output>
python -B scripts/planning.py build <output>
python -B scripts/planning.py check <output>
python -B scripts/planning.py advance <output> development|acceptance
python -B scripts/planning.py record <output> <结果JSON>
python -B scripts/planning.py invalidate <output> <失效原因>
```

check 分别输出 mechanical/readiness/acceptance。development 需上游就绪、待决解决、当前摘要的独立 PASS 与真实人工确认；acceptance 需所有任务 complete，每项必要检查有当前代码摘要与哈希绑定的 PASS 证据。record 拒绝阶段不符、过期摘要、缺文件/断言/实例或仅口头通过。模型变更使旧评审、确认、实测失效。

planningDigest 同时绑定工作定义与生成器规范/脚本/模板内容；升级 Skill 后必须重建和复审，不沿用旧算法下的确认。codeDigest 绑定已声明的代码根，代码变化使实测与开发检查失效。

代码修复前用 invalidate 把本轮实测标为待验收并保留失效说明，回到 development；计划含义改变则回到 planning 重新评审确认。当前文件原位维护，不复制历史版本。重新执行当前代码必要检查、advance acceptance 后才能登记复测，避免旧失败证据导致无法正常补录。
