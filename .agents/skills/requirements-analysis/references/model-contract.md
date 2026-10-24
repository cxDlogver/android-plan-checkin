# 模型数据契约

完整字段以 model.schema.json 为准。JSON 使用 UTF-8；ID 全局唯一且含义稳定。业务含义变更更新 revision。

sources 记录原文 path（相对模型）与 sha256。clauses 逐条记录 quote、locator、scope=included/excluded/context、scopeReason 和 coverageIds。included 条款必须有需求覆盖。语义审查还需检查是否漏登记条款；哈希不证明覆盖完整。

clarifications 记录 question、proposal、status=open/confirmed/excluded、resolution、confirmation.quote/conversationRef。确认必须是实际用户回答，程序不能认证对话真实性。open 阻塞正式建模。

状态、操作及需求的 sourceIds 引用 included clause 或已 confirmed clarification；每项至少引用一个 included PRD clause。澄清用于细化，不能代替全部 PRD 来源。

states：id/name/scope/businessFacts[]/verification.method/verification.assertions[]/sourceIds[]/isStart。scope 写明业务投影、参数及绑定关系；纯 UI、工程步骤和主观词不能当业务事实。

transitions：id/from/to/operation/actor/guard/effects[]/sourceIds[]。无附加条件 guard=true；不执行任意谓词字符串。effects 写清数据前后关系及禁止副作用，不替代目标节点。

atomicRequirements：id/transitionId/name/functionalRequirements/visualRequirements/sourceIds。
functionalRequirements：statement/acceptanceCriteria[]。
visualRequirements：applicability=required/not_applicable、criteria[]、reason。required 至少一条标准；not_applicable 必须解释且 criteria 为空。自主设计保留为设计边界。

nonTransitionRequirements：id/kind=delivery/quality/scope/name/functionalRequirements/visualRequirements/sourceIds。不进入业务原子需求图。

reviews：ruleId/entityIds[]/result=pass/fail/evidence。七类审查须覆盖对应全部实体：business-facts、observable-states、source-backed-states、real-operations、atomicity、visual-fields、scope-coverage。写具体审查证据。
reviewDigest：digest 命令的 SHA256，涵盖除 reviews/reviewDigest 外的模型语义；语义变化须重审。

导出均带 schemaVersion/analysisId/revision/modelDigest。状态图 nodes=states，edges=transitions。原子需求导出展开 sourceState/transition/targetState。需求图完整边集 E={(Ri,Rj,via) | to(Ri)=from(Rj)=via}，不混入开发依赖。

数据 Schema 与脚本使用 JSON Schema 的 type/const/enum/properties/required/additionalProperties/items/minItems/uniqueItems/minLength/pattern 子集，脚本不声称是通用 Schema 引擎。图与业务约束由额外门禁完成。

scenarios 为有来源的验收需求序列，含 id/name/sourceIds/bindings/requirementIds/expected。脚本核对相邻需求终态/始态严格相等；bindings 仍须由审查证明可满足，不允许用虚假操作衔接验收链。
