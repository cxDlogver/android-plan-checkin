# Test Case数据与验收规范

## 目录

- [文件关系](#1-文件关系)
- [用例字段](#2-用例字段)
- [视觉与功能验收](#21-视觉与功能验收)
- [测试类型与环境](#22-测试类型与环境)
- [证据形式](#23-证据形式)
- [测试数据与Mock](#3-测试数据与mock)
- [验收路线](#4-验收路线)

## 1. 文件关系

最终test-cases.json绑定正式stateGraph和atomicGraph；sha256使用上游canonical JSON摘要。inputs保存PRD和授权规则等直接文件引用，使用原始字节摘要。task-plan.json通过testCases摘要绑定同版用例图，引用摘要不构成循环。

案例文件根字段为schemaVersion、title、revision、stateGraph、atomicGraph、inputs、dataProfiles、cases、edges和coverage。edges、coverage由脚本生成；其余内容由资料与代码分析确定。通用结构见[Schema](../assets/test-cases.schema.json)。

## 2. 用例字段

| 字段 | 含义与要求 |
| --- | --- |
| id/title | 稳定身份与可读验收目标 |
| kind | primary主需求、constraint全局规则、regression存量直接影响 |
| requirementId | primary唯一对应的原子需求；其他为null |
| given.stateId | primary引用原迁移from；独立补充用例为null |
| given.setup | 起点具体准备方法或沿路线继承方法；独立用例说明隔离准备及可观察的已知事实 |
| given.verify | 动作前怎样核对前提，失败时不继续执行动作 |
| operation | 本次动作，内嵌label、actor及必要input；primary与原迁移完全一致，不建operationID |
| expected.stateId | primary引用原迁移to；独立补充用例为null |
| expected.conclusion | 可读结果；primary的正式断言以终态全部事实和迁移effects为准，文字摘要不减少验收范围 |
| dataProfileId | 本次使用的数据契约，引用共享dataProfiles |
| mocks | 仅实际需要的依赖替身；无替身为[] |
| acceptance | 分别包含visual和functional；每组记录applicable、reason、checks，至少一组适用 |
| constraintIds | 由本用例专门覆盖的全局规则；不重复抄写规则 |
| impactId | regression关联task-plan中的直接损害分析，其他为null |
| execution | 规划固定status=not_run、actual=null、evidence=[] |

主用例的given和expected通过同版正式图解析，不复制事实数组。初态是执行前必须成立的事实，condition仍是动作后的结果分支；不要把用例准备步骤写成新条件。

### 2.1 视觉与功能验收

每个用例都填写两组验收。适用性由本用例要证明的事实决定，不由所用工具决定。

| 分组 | 验收对象 | 不纳入本组的情况 |
| --- | --- | --- |
| visual | 可见内容、选中表现、样式、布局、适配及从当前画面到目标画面的呈现变化 | 需求未要求任何可见表现，且本例仅检查内部规则或功能边界 |
| functional | 需求明确要求的交互约定（如入口、返回及输入保留）、数据变化、计算、权限、提交、持久化、对外调用或禁止副作用；定向回归中的存量事件契约 | 仅模拟视觉响应，且本例没有另需验收的交互约定或业务效果 |

每组applicable为true时，reason说明需验收的事实，checks至少一项；为false时，reason说明不适用的范围依据，checks=[]。至少一组适用。主用例涉及初态或终态的视觉事实时不能省略视觉验收；存在功能事实时不能省略功能验收。effects按实际观察对象归类。

同一动作可以同时引起两类事实，分别登记相应检查；同一张截图或同一次验收执行可以被共同引用，但须分别说明它支持什么结论。视觉浏览不能因为使用脚本验收而被改称功能完成；功能事实也不能仅用成功提示代替真实结果。

### 2.2 测试类型与环境

每项checks记录testType、environment、criterion、oracle、procedure、evidence和sufficiency。criterion用自然语言写明通过标准；oracle、procedure、sufficiency保存独立求预期的方法、实施步骤及方法充分性的说明，供实施和审查使用。

testType只允许script（脚本验收）和browser（浏览器验收）。environment单独说明实际执行环境：runtime（测试运行器）、browser（浏览器）、native（原生应用宿主）。单元、组件、集成及端到端等实现范围可在procedure中说明，不再作为验收类型。

| 验收类型 | 执行方式与适用范围 | 环境与常用证据 |
| --- | --- | --- |
| 脚本验收 | 执行命令、测试运行器或原生设备驱动，检查规则、状态协作、调用边界或原生界面 | 测试运行器：检查结果、组件树、状态快照、调用记录；原生宿主：另可采集实际截图、原生节点树和布局测量 |
| 浏览器验收 | 在真实浏览器页面中执行交互并观察内容、排版、滚动、焦点等；可手动或自动化执行 | 浏览器：检查结果、实际截图、DOM结构和布局测量 |

使用真实浏览器的检查填写browser及environment=browser；其他脚本检查填写script，环境为runtime或native。仅有测试运行器不代表已经有真实界面；脚本调用实际原生设备时才可提供该设备的截图与运行时节点层级。浏览器自动化归为浏览器验收，避免同一检查被任意归入两类。

脚本已经足以证明的结论不再重复安排浏览器验收。需要真实排版的结论应在实际渲染环境观察，不能用模拟DOM或样式对象快照冒充。运行环境与取证能力须一致。

### 2.3 证据形式

evidence中的每项为{form,description}，均为本项检查必须取得的证据。description写明要记录的对象、预期与实际对照内容；“截图/DOM任选”“测试结果”等含糊词不能替代明确选型。

| form | 页面名称 | 记录内容 |
| --- | --- | --- |
| screenshot | 界面截图 | 实际渲染画面及对应输入、环境、版本；预期参考图与执行截图分别标识 |
| dom | DOM结构 | 浏览器实际DOM、文本、语义属性及定位；不能用原生节点树冒充DOM |
| native-tree | 原生节点树 | 实际原生控件层级、文本、可访问属性和选中/禁用状态 |
| component-tree | 组件树 | 测试渲染器产生的组件结构及属性；说明它不代表真实排版 |
| layout-measurement | 布局测量 | 实际节点的位置、尺寸、滚动/焦点、遮挡及环境尺寸 |
| assertion-report | 检查结果 | 检查目标、独立预期、实际观察和逐项结论，可为自动断言或明确的人工对照 |
| state-snapshot | 状态快照 | 动作前后需验收的数据或功能状态 |
| call-trace | 调用记录 | 调用时机、次数、参数及响应 |
| data-snapshot | 测试输入 | 本次解析后的输入、对象选择及跨步骤沿用关系 |

每项检查至少保留检查结果。截图和布局测量来自实际浏览器或原生宿主；DOM来自浏览器；原生节点树来自原生宿主。纯规则验收可以仅使用包含预期及实际值的检查结果，不强制截图。功能验收不能只用截图作完成证据；视觉验收的证据须覆盖所声明的可见标准。

预期结果关联UI图时，HTML在预期结果中展示该图，图像从正式终态的UI来源解析，不复制到新目录。它用于理解应到达的画面，标注为“预期 UI 参考图”；动态名称、日期等示例值仍按实际输入和UI结构核对。预期图不写入execution.evidence，也不能充当本次实际截图。

测试通过结论应绑定实际执行证据，计划中列出所需形式不能充当已经采集到的证据。规划阶段execution.status仍为not_run、actual=null、evidence=[]；HTML将它显示为“未执行”。执行前置资料缺失单独显示待准备项，不自动生成失败或通过结论。

## 3. 测试数据与Mock

### 3.1 数据契约

每个dataProfile包含id、scope、preparation、continuity与fields。scope为route时在一次合法路线段中保持同对象输入，case只用于可独立准备的测试。

fields逐项声明name、type、mode和source。source直接定位原文档/结构的条款或JSON Pointer。mode=literal时必须有value且没有resolve/oracle；mode=context时必须有resolve及oracle且没有value。type采用需求定义的展示类型或明确JSON类型，不将截图样例当默认值。

| 值的性质 | 表达方式 |
| --- | --- |
| 稳定分支枚举、协议常量、独立边界值 | literal，给出具体值与依据 |
| 当前对象ID、名称、版本、前序选择、运行时日期 | context，说明读取哪个上下文及生命周期 |
| 与真实页面绑定的数量、结果或选择项 | context，记录选择规则和稳定定位；不硬编码列表第几项或上次截图中的文字 |
| 同一对象在后续页面出现的字段 | 沿用路线对象或明确映射，不重新随机生成 |
| 边界/长文本矩阵 | 固定数据可以作为本次独立输入，但不得覆盖路线中已经成立的对象事实；改变输入时从允许入口重开场景 |

context的预期根据规范和已捕获输入独立计算，不能读取被测输出再当成预期。执行时保存解析后的真实值；值尚未产生不伪造实际记录。某字段规则无法确定时澄清，不用任意值填补。

### 3.2 Mock边界

Mock记录boundary、purpose、trigger、lifetime、response、verification与restore。response可以是literal及value，或context及resolve/oracle，规则与数据字段相同。

Mock替换网络、时钟、平台或场景端口等外部边界，不能替换正在验收的布局、事件处理、目标状态生成或断言函数。声明调用时机与次数，动作之前仍处于given，动作触发后才交付结果；验证正确参数及调用发生，测试结束恢复，不向后续测试泄漏。

primary存在condition时至少一个Mock的response或实际结果准备须明确对应condition.match。当前脚本支持确定的literal结果样例；不适合固定响应的场景使用context响应及matches=condition.sampleOutcome作结构化分支见证，value仍不得写死。matches只见证分支枚举，动态载荷继续由resolve处理。对于无需Mock的真实分支，以boundary=real-result声明实际控制边界、结果准备与观察，不伪称依赖已被模拟。

没有condition时不添加伪造分支见证；确有集成依赖替身仍可使用Mock，说明其边界用途。Mock命中某分支只证明该路径的UI或消费者行为，不自动证明真实服务能产生此结果。

## 4. 验收路线

主用例按原子图coverage.sequence一一映射，前后共享同一stateId才是handoff；否则后项必须是正式起始用例并标为restart。不能复制每个用例的beforeEach把非起点改成起点。

全局检查与定向回归用例具备完整隔离fixture且不承接业务事实，作为独立入口，各访问一次，按id排序追加。独立用例结束后只有其他独立入口或正式起始主用例可进入，不与任意非起点建立状态衔接。

删除独立用例后，任何合法完整序列的主用例投影仍是一条合法需求序列，因此主用例至少需要上游已证明的M次访问；K个独立用例各至少访问一次。映射上游最优序列再追加K项，达到M+K。脚本以相同初终态建立计算投影，复用精确最小费用算法再次核对下界。固定种子、启发式或任意生成树不作为最优证明。

coverage记录algorithm、optimality、sequence、visitCount、minimumVisitCount、additionalVisitCount与primaryMinimumVisitCount。图边按序列相邻对首次出现顺序编号，只存一次；sequence保留每次重复访问。最少访问针对逻辑用例，不将一个用例内的环境矩阵行、多个断言或多层测试算作新增图节点。

后续执行必须核对当前步骤的given，普通衔接继承前项已验收终态，restart才重新准备。检查失败即停止该路线段并记录实际结果，不因计划允许到达而宣称测试已通过。

## 5. 执行结果衔接

规划阶段 execution 固定为未执行。执行阶段按[代码执行规范](../../code-execution/references/evidence-and-status.md)写入实际观察、逐检查与逐访问结果、证据引用，并同步 HTML。Schema 的执行状态字段供该阶段使用；本 Skill 的 build/check 仍要求初始规划状态，不用于覆盖已执行记录。验收定义、来源、数据契约和最少路线不随状态回写改变。
