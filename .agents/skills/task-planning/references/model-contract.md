# 规划模型契约

Schema 是字段契约。JSON UTF-8，Case/Task ID 在模型内全局唯一且含义稳定；步骤 ID 在各自用例内唯一，业务或计划内容变化更新 revision；reviewDigest 覆盖除 reviews/reviewDigest、execution、各用例 actualObservation 外的规划语义。

source 包含 requirementsPath/requirementsSha256/requirementsDigest/gatePath/gateSha256。路径相对 planning-model.json；源模型 SHA 与上游门禁摘要均需一致，且上游为 PASS。默认读取上一阶段通用 analysis-model.json，不限定业务产品。

executionPolicy：allowedLevels、browserAcceptance=false、fixtureMode=isolated、onFailure=stop、entryRule=previous_passed_edge、rootRule=no_external_preconditions。若已有共享状态用例，应先显式调整契约和规划，不静默伪装为 isolated。

cases：id/kind=primary|supporting|scenario/requirementIds/name/level=unit|integration/environment/fixture/steps/expectedResults/actualObservation/testFile/plannedCommand/limitations。primary 和 supporting 均只映射一项来源需求；每条原子需求恰一个 primary，每条非迁移要求恰一个 supporting。scenario 可映射多个原子需求，必须有 mappingRationale，不替代默认 primary。

fixture 包含 setup/cleanup/externalPreconditions[]，隔离夹具不消费其他用例产物。steps 每项 action/expectedResultIds；至少一步准备、操作、观测和清理，不能只写“执行测试”。expectedResults 每项 id/expected/observe/criterionRefs[]，criterionRefs 如 R01:F:0、R01:V:0，索引对应来源的 functionalRequirements.acceptanceCriteria 或 visualRequirements.criteria。完整覆盖每项来源标准，避免把模糊步骤当完整预期。

actualObservation：status=not_run|pass|fail、observedValues[]、assertionResults[]、evidence[]、note。执行前必须无实际值、断言结果与证据。真实执行证据记录 path/sha256/command/exitCode；逐断言观测记录 assertionId/actual，结论记录 assertionId/status。不能把“已建立计划”当成用例 pass。

graph：roots[]、edges[]（from/to/reason）。traversal：route[]、repeatCount、lowerBoundVisits、optimality=proven_optimal|heuristic、proof。route 覆盖全部用例，相邻必须有边，首节点是无入边根；proven_optimal 只在每项访问一次、访问数等于节点数下界时由内置验证器认可。

plan：objective/baseline/decisions[]/modules[]/tasks[]/commands[]/verificationLimitations[]/references[]。模块有 path/responsibility；任务有 id/title/dependsOn/requirementIds/caseIds/outputs/steps/doneCriteria/status=planned，开发依赖必须无环。所有用例和来源需求须进入具体任务；命令是计划命令不是执行证据。

execution：runId/implementationRef/modelDigest/visits[]。首次未运行时前两项为 null、visits为空。访问项 caseId/status/observedValues/assertionResults/evidence；每次访问必须依路线前进且前序为 pass，逐断言均有真实值。证据文件可读且 SHA 匹配；模型摘要绑定本次规划，禁止跨运行复用历史 pass。

reviews：ruleId=semantics|case-oracles|fixtures-and-order|implementation-plan|verification-boundaries、result=pass|fail、evidence。记录真实逐项检查理由，不自动认证业务或测试结果。

脚本的 Schema 检查支持 type/const/enum/properties/required/additionalProperties/items/minItems/minLength/minimum/pattern/uniqueItems；其余业务约束由门禁完成。Markdown 和 JSON 派生文件不得手改。
