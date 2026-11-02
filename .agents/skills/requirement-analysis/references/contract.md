# 状态迁移图数据契约

格式版本2.0.0。文件路径相对state-transitions.json及其HTML。目录：

- [独立工作记录约束](#独立工作记录约束)
- [起点依据](#起点依据)
- [动作覆盖](#动作覆盖)
- [最终图](#最终图)
- [直接来源](#直接来源)
- [状态](#状态)
- [迁移与动作](#迁移与动作)
- [分支条件](#分支条件)
- [全局约束](#全局约束)
- [校验与交付](#校验与交付)

## 独立工作记录约束

[analysis-work.schema.json](../assets/analysis-work.schema.json)单独约束需求分析和澄清工作记录，包含资料、范围映射、澄清及审查定义。[state-transitions.schema.json](../assets/state-transitions.schema.json)只约束最终图，不包含工作记录的字段或定义。

工作记录固定为最终图目录下的.work/analysis-work.json，资料路径统一相对最终图目录解释。analysis-work.schema.json作为长期规范保留，工作记录实例在任务完成后删除，不导出到Canvas页面。

| 工作字段 | 填写内容 | 完成判定 |
| --- | --- | --- |
| workSchemaVersion | 固定1.0.0 | 使用analysis-work.schema.json契约 |
| documents | 每份资料的source、role、authorization和version | 至少登记当前PRD，引用有效，最终图使用的文件均已登记 |
| requirements | source、classification、reason、targets；纳入项另有actionAnalysis | 事实与动作均逐项识别；纳入项有目标，排除/上下文无目标；所有最终实体有纳入项映射 |
| entries | 每个起点的stateId、kind、source、method；无边状态另有isolationReason | 与全部起点一一对应，来源支持入口或准备方法，并保留于状态source |
| clarifications | question、impact、status、answer、resolution，按需proposal和resolutionSource | open项已处理；resolved项有实际回答、对话引用和处理结论 |
| reviews | scope、facts、operations、inheritance、branches、coverage六项的status与evidence | 六项均passed且有具体依据，entries与actionAnalysis的逐项检查同时通过 |
| graphSha256 | 审查时实际图文件SHA-256 | 与当前图文件一致 |

source使用本契约的直接文档或UI格式。documents.role为prd、ui或supplement，authorization说明使用依据，version未标时为null。requirements.classification为included、excluded或context；targets每项为{collection,id}，collection只取states、transitions或constraints，id须存在于最终图。

requirements先依据正式来源识别事实和动作，再关联targets。included项必须填写actionAnalysis；excluded和context项不填写该字段。图实体全部有映射与需求动作全部得到处理分别检查，不能互相替代。

clarifications中未回答时answer和resolution为null，status=open；实际回答后answer={text,conversationRef}，resolution为处理结论，status=resolved。若回答改变正式需求，resolutionSource定位已更新的正式文档。没有问题时clarifications=[]，按实际资料分析结果填写。

工作记录中的映射用于范围与覆盖检查；最终图不引用这些工作条目。source的语义支持关系、实际回答真实性和审查结论仍需结合原文判断，脚本验证字段、引用及完成记录的一致性。

scripts/work.py提供init、check和finalize：init按analysis-work.schema.json的const、default与类型初始化工作记录，且不覆盖已有记录；check只读取工作记录及图，检查资料、范围映射、起点依据、动作覆盖、澄清、六项审查和图哈希，结果输出到终端；finalize还检查HTML同步，全部通过后删除本次工作副本及空目录。证据缺失、未完成或检查失败时保留工作记录。额外文件须核对归属，不自动递归删除。

Skill内的analysis-work.schema.json与state-transitions.schema.json分别保留；每次任务的工作记录在完成后删除。分析和澄清记录不进入JSON或HTML中的最终状态图。

### 起点依据

entries逐个对应isInitial=true的状态，不重复登记，也不登记非起点。每项字段如下：

| 字段 | 含义 |
| --- | --- |
| stateId | 对应的起点状态ID |
| kind | direct表示正式来源支持直接进入；prepared表示来源支持独立准备该场景 |
| source | 定位支持入口或准备方式的正式原文 |
| method | 实际进入方法；需要准备时说明步骤、对象和必要输入 |
| isolationReason | 仅无入边且无出边时填写，说明独立验收依据及范围内没有前驱、后继动作的原因 |

source采用直接document格式，path、locator、sha256、quote必填；locator定位具体条款、入口标注或准备说明，不使用$概括整个文件。UI中的入口或交互标注可按结构文件的JSON Pointer直接引用。文件存在、画面外观或页面清单本身不证明可直接进入。

起点source中保留同一直接引用，使工作记录清理后仍可回溯依据。匹配时路径、位置和哈希等身份字段一致，quote和version为附加说明。method及isolationReason的内容须由来源实际支持；步骤不能确定时按澄清流程处理。准备分析入口时，范围内仍需独立验收的动作保留为迁移。

起点缺少记录、无边状态缺少独立依据时，entry-evidence阻断定稿；重复记录、指向非起点、与状态来源不一致时检查失败。多个合法起点及有明确依据的独立静态场景可以保留，图不要求为了连通而补边。

### 动作覆盖

纳入要求的actionAnalysis={status,evidence,actions}。status取pending、passed或failed，初始为pending；evidence说明已核对的原文或UI范围、识别依据和判断结果。actions为空时，说明本项要求为何没有明示动作或可推出的必要步骤。

每个候选动作内嵌operation，不设置动作ID：

| 字段 | 含义 |
| --- | --- |
| from | 已确定的初态ID；未确定或范围外且未建态时可为null |
| operation | {label,actor,input?}，与最终迁移使用相同动作语义，无id，无输入时省略input |
| basis | explicit为明示动作，necessary为由已确定事实推出的必要动作 |
| change | 明确动作作用对象及预期可观察变化，说明初态、动作和终态的关系 |
| disposition | modeled、excluded、constraint或open |
| expectedTargets | 来源要求的结果状态ID数组；modeled时非空 |
| transitionIds | 本候选动作对应的迁移ID数组；modeled时非空，其他处理为[] |
| reason | 动作依据或处理结论的具体理由 |
| resolutionSource | excluded时必填，采用含具体位置与原文摘录的直接document引用 |
| constraintIds | 仅constraint时填写，指向覆盖此项验证的既有全局约束 |

候选动作的来源继承所属requirement.source。每项处理按下表判定：

| disposition | 完成判定 |
| --- | --- |
| modeled | from存在；operation、输入及初态与引用迁移一致；实际终态集合等于expectedTargets；迁移已列入本要求targets，且其source保留本要求的直接引用 |
| excluded | 引用明确排除该动作效果的条款，说明范围判断；expectedTargets和transitionIds为[] |
| constraint | 说明本项只是按既有规则验证，没有独立状态变化；expectedTargets和transitionIds为[]，constraintIds存在且列入本要求targets |
| open | 动作、对象、路径或结果尚未确定，阻断定稿；transitionIds为[]，影响验收的歧义按第1节澄清 |

operation的匹配沿用[分支条件](#分支条件)中的初态、执行者、动作名称和输入归一规则。同一要求内语义相同的候选动作合并；不同来源可分别支持同一迁移。来源身份匹配忽略quote、version附加说明，其他字段一致。

每条最终迁移至少对应一项已建候选动作。漏建候选结果、引用错误的迁移、只有实体targets而没有动作分析、已建边与排除或规则覆盖结论冲突时，action-coverage检查失败。pending或open保持阻断，六项reviews的passed不覆盖这些结果。

字段、引用、结果集合及映射的一致性由脚本检查；动作识别是否完整、原文是否支持入口和因果关系、无动作或排除理由是否成立，结合原文逐项进行语义审查。事实、动作及其处理记录只保存在工作副本，最终图继续使用下述状态、迁移和全局约束契约。

## 最终图

| 字段 | 含义 |
| --- | --- |
| schemaVersion | 固定2.0.0 |
| title / revision | 图标题和正整数修订号 |
| states | 事实状态数组 |
| transitions | 迁移数组，每条内嵌operation |
| constraints | 全局约束数组 |

分析摘录、范围分类、澄清、审查和检查结果属于临时工作资料，保存在图文件之外，完成后删除。最终图的引用只指向正式来源文件或图内状态端点。

state、transition和constraint的id在图内唯一，修改表述时保持稳定；from和to必须指向现有状态。事实、动作及来源引用通过所属实体表达，不另建注册表。revision在事实、动作、结果或约束含义变化时递增。

## 直接来源

状态、迁移和全局约束各有非空source数组。每项引用直接文档或UI，不经过来源注册表或分析条款ID。

文档引用：

~~~json
{
  "kind": "document",
  "path": "../source-resource/prd/需求.md",
  "locator": "L14-L16",
  "sha256": "<实际文件SHA-256>",
  "quote": "对应原文"
}
~~~

path、locator、sha256必填；quote和version仅在需要原文或已标明版本时记录。Markdown等文本使用行号或真实章节标题定位；JSON使用JSON Pointer，$表示整个文件。

locator应能定位到支持该实体的要求：行号须在文件范围内，章节标题须存在，JSON Pointer须能解析。quote按该位置的实际内容摘录。sha256按文件字节计算；来源变更后重新读取并审查相关事实，再更新引用。

UI引用：

~~~json
{
  "kind": "ui",
  "structurePath": "../ui-spec/documents/示例页面.json",
  "documentId": "ui-example",
  "nodeIds": ["root"],
  "structureSha256": "<结构文件SHA-256>",
  "screenshotPath": "../source-resource/ui/示例页面.png",
  "screenshotSha256": "<原截图SHA-256>"
}
~~~

UI引用全部字段必填。documentId与结构文件的身份一致，nodeIds属于其节点树；结构和原截图分别登记实际哈希。原截图用于展示来源，实际预期取值由已确认的UI规范决定。

所有引用使用授权项目内的相对文件路径。文件可读取、位置有效及哈希一致是引用通过条件；加密设计文件通过对应工具读取后使用已确认的结构资料。资料冲突按已约定优先级处理；影响验收且没有优先级时澄清。需求来源的范围与含义在定稿审查中确认。

## 状态

| 字段 | 含义 |
| --- | --- |
| id / title / statement | 稳定身份、简短标题、共同成立的事实 |
| isInitial | 全图的直接入口或已明确可准备的场景；区别于某条迁移的from初态 |
| source | 直接文档或UI来源 |
| functionalFacts | 功能事实数组，无此类事实时[] |
| visualFacts | 视觉事实数组，无此类事实时[] |

两类事实至少一类非空。每项事实包含statement、assertion和observation。事实来源继承该状态source；视觉状态source中必须有结构与原截图引用。

statement按“对象—属性或内容—期望值”明确事实；同一状态的事实同时成立，能够按observation检查，并由assertion判定是否满足。functionalFacts可为空，visualFacts可为空；视觉或功能事实单独存在时仍按相同的来源、观察和验收要求审查。isInitial表示本分析范围可直接设置或进入的入口，可有多个入口；它不指定产品默认启动页。

assertion={path,op,value}：path定位观察对象，op指定判断方式，value保存实际期望。

| op | value要求 | 适用内容 |
| --- | --- | --- |
| eq | 明确的JSON期望值 | 属性或内容相等 |
| in | 非空期望值数组 | 属性属于有限取值 |
| exists | 布尔值 | 对象或内容是否存在 |
| count-eq | 非负整数 | 项目数量 |
| matches-ui | documentId、nodeIds、structureSha256 | 指定UI节点及后代的视觉呈现 |
| eq-ref | before.*、input.*、outcome.*或after.*字段路径 | effects中的前后数据关系 |

observation={method,locator}说明如何观察以及观察位置；期望由陈述和断言给出。观察方式可使用实际界面、查询或其他已确认渠道，位置应能指向对象或节点。占位性描述不作为通过标准。

matches-ui用于视觉事实，value={documentId,nodeIds,structureSha256}须匹配状态的某项UI来源。验收时将实际呈现映射到节点ID，按已引用的结构、样式库和适用规则在当前环境求值，比较层级、顺序、文字、资源、布局与外观。固定文字直接比较；动态占位按所引用UI规范和本次场景输入解析后比较，不把来源中的示例值登记为固定事实。

source、decisionRefs等来源元数据不作为视觉属性；环境托管节点按其所有权规则处理。使用的资源及字体应满足规范，缺失资源或未执行对照分别记录为未满足或未执行。具体差异按节点记录，像素相似度阈值以已确认要求为准。脚本只检查引用关系，不执行该视觉断言。

状态的新建、复用和不建规则见[SKILL.md第2.3节](../SKILL.md#23-判断新建复用还是不建状态)，前提延续与路径汇合见[第2.4节](../SKILL.md#24-处理已知前提与路径汇合)。

不同状态应体现需求要求区分的验收标准，或影响后续动作与结果的前提差异。等价场景复用状态，普通参数变化使用动作输入或验收数据。此前有效的同一对象事实沿路径延续；多路径汇合时，核对后续动作所需前提在每条路径上均一致。

## 迁移与动作

| 字段 | 含义 |
| --- | --- |
| id / from / to | 迁移身份和初、终态ID |
| operation | 本条迁移自己的动作对象 |
| source | 支持该动作和结果的直接来源 |
| condition | 存在实际结果分支时记录，否则省略 |
| effects | 终态之外需表达的可观察关系，否则省略 |

operation={label,actor,input?}，没有id。label明确动作，actor明确执行者与场景；input只记录本次迁移必需的数据，无输入时省略该字段。相同动作出现在不同迁移中时分别内嵌。

明示动作由正式来源直接支持；必要动作由已确定的初态及目标事实确定。两者的作用对象、输入和结果应明确，动作效果在范围内。两种依据的判定规则见[SKILL.md动作依据](../SKILL.md#31-动作依据)；推导过程留在工作资料，定稿的source直接定位支持动作与结果的正式内容。

确定动作示例：

~~~json
{
  "id": "T1",
  "from": "S1",
  "to": "S2",
  "operation": {"label": "展开详情区域", "actor": "用户"},
  "source": [{"kind": "document", "path": "../需求.md", "locator": "L8", "sha256": "<实际哈希>"}]
}
~~~

初态事实描述动作前已成立的前提，operation.input描述本次选择或提交的数据。effects仅用于终态未表达的前后数据关系；每项有statement和assertion。eq-ref仅用于effects，value为before.*、input.*、outcome.*或after.*字段。

自环应有可观察效果，且动作后仍满足原状态的事实。状态的识别或验收事实改变时建立相应终态。重复验证全局适配规则的测试输入留在该规则或其引用矩阵中。condition、effects和input只在有实际内容时出现，空对象、空数组或占位条件不用于补齐格式。

## 分支条件

分组键为from、规范化后的operation.actor和label、canonical(operation.input或{})。actor和label归一空白并忽略字母大小写；canonical按对象键排序，统一1与1.0等语义相等的数字。相同动作使用一致名称与执行者，输入记录真实参数。

单一确定结果省略condition。同组有多个动作后才出现的可能结果时，各分支均记录condition，每项包括：

- statement：可读结果条件。
- match：outcome.*字段与非空标量取值数组；字段之间AND，取值之间OR。
- sampleOutcome：满足match的结果样例，可用于响应Mock。
- observation：结果的观察方法和位置。

每个条件必须存在不满足它的其他分支。同组条件须互斥，且目标或可观察效果不同。条件存在但只有一条边、重复语义条件、无条件边与条件边混用、条件不改变结果均不通过。

匹配字段之间为合取关系；任一共同字段的取值集合无交集时，两条件互斥，否则可能重叠。sampleOutcome须满足对应match；结果样例用于实例化该分支，需求全文用于确认实际分支覆盖。缺少影响验收的结果定义时进行澄清。

动作前已确定的事实、已选输入和全局规则不写入condition。全局规则中的适配区间等判断直接引用其原规范；仅当产生不同迁移结果时，才建立分支条件。

## 全局约束

每项为{id,statement,source}，对全图统一生效。规则已存在于正式文档或UI规则文件时，source定位该文件及相关位置，statement说明适用要求，具体取值维护在原文件。

同一规则只保留一处。状态事实、初态前提、动作输入及终态结果各保留在所属位置；后续步骤沿用有效前提与规则。语义审查负责识别等价和已被涵盖的约束；脚本检查完全重复的规则及事实。

## 校验与交付

校验包括Schema、直接来源文件与哈希、节点与事实、动作字段、真实分支与确定性、可达性、重复约束及HTML同步。分项通过标准及执行流程见[SKILL.md审查与校验](../SKILL.md#7-审查与校验)。脚本输出到终端，不修改JSON或留下报告。

常见状态与迁移问题的修复图见[常见问题与修复示例](state-transition-examples.md)。语义审查覆盖范围、事实、动作及结果、前提与规则、分支确定性和完整覆盖。每项依据真实来源判断：脚本可确认引用有效和结构一致，自然语言范围、动作必要性、分支是否完整及等价规则去重需要阅读原文。检查失败、证据缺失或需求未确认时，处理受影响内容后再定稿。

原文或图的含义变化后重新审查相关部分。已登记实体全部有source，不等于PRD全文已完整覆盖；覆盖审查逐项对照本轮要求及UI清单完成。

HTML内嵌同版JSON及哈希，使用Canvas展示图。页面内容、默认布局、拖拽与选中层级、聚焦范围、侧栏切换和验收按[HTML设计规范](html-design-spec.md)执行。展示位置与可见性属于HTML的临时视图状态，不加入最终JSON；数据字段及来源要求仍按本契约处理。

交付state-transitions.json、state-transitions.html、atomic-requirements.json与atomic-requirements.html。原子图按[原子需求图规范](atomic-requirements.md)引用状态图并确定性派生，不改变本契约对状态、迁移及全局约束的限定。按独立工作记录约束完成分析、澄清及定稿检查，finalize检查工作记录及两张图后清理工作副本；正式需求与UI资料、Skill中的各份Schema保留。结构检查通过与应用功能、视觉验收分别报告。
