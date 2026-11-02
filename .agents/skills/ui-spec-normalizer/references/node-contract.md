# 节点与交付契约

使用assets/ui-spec.schema.json建立包，Schema的字段结构为本Skill自定义格式，不冒充Figma或pen原生导出。以下语义与Schema同时生效。

## 1. 包与权威边界

默认最终产物如下，具体页面与资源数量随本次输入范围确定：

```text
ui-spec/
  manifest.json
  rules.json
  library.json
  documents/具体页面或组件标题.json
  assets/最终JSON或报告依赖的资源与证据（按需）
  schema/ui-spec.schema.json
  UI规范.md
  validation-report.json
```

分析结论和必要的差异说明写入UI规范.md；校验状态与限制写入validation-report.json，不按执行步骤逐项增加报告。图片、字体、预览或工具仅在最终交付实际使用或用户要求时保留，缺失信息如实记入issues。

中间产物用于本次处理或恢复，不作为默认交付。任务完成后删除本次产生的原始节点快照副本、抓取缓存、临时转换／审计脚本、调试输出、重复截图和过程日志。清理前把需要追溯的来源标识、版本、决策及校验结论写入现有字段或报告，并检查最终文件不依赖待删除的临时路径。最终JSON引用的资源、报告引用的必要验收证据及用户原有资料保留。

路径均相对包根，禁止绝对路径或越出包根的路径。sources中保存的来源URI仅作provenance，不是运行依赖。hash为文件原始字节的SHA-256。输出文件名使用具体标题；ID独立于文件名，引用只用ID。

authority=draft：结果可用但仍有关键歧义或缺失；authority=canonical：唯一有效基准。将旧资料改为留档需要用户对“以后只按JSON对齐”的授权，本Skill本身不扩大任务范围。

每个record带schemaVersion=2.0.0和kind。manifest登记全部document及其file/hash；rules、library也登记file/hash。document的kind区分screen、component、reference。说明资源不能影响端型判断或算作应用页面。

sources列出本次允许使用的来源和revision；排除范围写在生成的UI规范中，不扫描历史目录补齐。sources.sha256允许null以支持无文件哈希的连接器，但需明确revision或已观察时间，不能伪造来源哈希。

## 2. manifest字段

- schemaVersion、kind=manifest、authority：版本与生效状态。
- sources[]：id、uri、revision、sha256，记录实际来源。
- documents[]：id、title、kind、profileId、file、sha256。profileId必须存在于rules.profiles。
- artifacts：rules和library的file/hash，指向包内文件。
- issues[]：id、documentId或null、message、critical、status=open/resolved、resolution或null。
- verification：baselineVisual、responsiveVisual分别为not-tested/passed/failed；视觉passed需要evidence[]中包内真实文件的相对路径作为证据，不能通过结构校验自动填写。

页面不足、资源缺失、原始关键属性不能表达等应产生issue。解决记录保留，不能只为通过删除失败项。

## 3. rules和profile

rules含固定classification、decisions和profiles：

- classification必须与布局指南中的768逻辑像素规则完全一致，不可修改阈值。
- profiles只允许mobile和desktop两个键，profile.formFactor必须与键一致；没有输入的类不创建UI。
- 不记录运行平台或分类证据字段。几何和字号的units固定为logical-px。
- decisions保存{statement,origin,evidence}，区分提取规则、归一化决策和用户要求。
- environment包含baselineWidth、baselineHeight、fontScale、locale、theme及环境遮挡、键盘、滚动规则；基准宽度必须属于该类。
- modes保存{id,when}。when允许width、height、fontScale、orientation、theme；width为完整页面可用逻辑宽度，布局断点不增加端型；base是隐含的唯一兜底。
- 同profile的非base模式条件必须互斥；数值区间为左闭右开[min,max)，null端点表示在当前profile内不设该侧边界；条件必须在本profile内存在可命中的宽度。
- validationCases的每个width必须在当前类别内；跨类UI另建对应profile，不在同一类中混测另一类页面。
- 取得不了逻辑宽度时保存draft、来源和关键issue，不创建第三类；draft允许documents和profiles暂时为空，不能发布canonical。

## 4. document字段

id、title、kind、profileId与manifest一致。referenceSize保存已确认的逻辑width和height；screen按其width与768比较得到profileId，高度不参与分类。component继承关联页面类别，reference不参与分类。tree是完整展开的唯一树，每个document保存自己的issues引用。原始观测仅作来源审计。

variant.state及properties仅描述当前确定样例，不生成业务状态机；不同已知状态可以形成有明确身份的document，不作为未决结构候选。

组件可用componentRef建立一致性关系，本版采用展开快照：document不在运行时再次继承组件树。若需要真正的模板实例系统，应发布新schema版本并定义覆盖顺序，不能同时使用展开节点与隐含继承。

## 5. node通用字段

| 字段 | 含义 |
| --- | --- |
| id / name | 唯一稳定身份／人可读名称；名称可重复 |
| kind | container/text/image/vector/shape |
| role | 已知视觉角色或null；不自动当作业务事件或读屏角色 |
| variant | 保存当前捕获的视觉state与组件properties；未知state为null，组件轴保存其实际标量值 |
| parentId / children | 父身份／有序子树；根为null，叶节点children为空 |
| ownership | 渲染归属：application由应用绘制；platform由环境托管（如系统栏），不表示运行平台类型 |
| componentRef | 对应component document的ID或null |
| layout | 仅container有值，且只能是Flex、Grid、Overlay之一 |
| sizing | width、height各一份{mode,value,min,max} |
| placement | 选定的定位与Flex／Grid分配属性 |
| overflow | x/y各为visible/clip/scroll，规定滚动与裁剪 |
| styleRef | 唯一library.styles引用，不另存一套运行CSS覆盖值 |
| content | text、image、vector对应内容；其他节点为null |
| semantics | 已定义的语义角色、label、actionRef；未知可null，不从图标名字猜动作 |
| policy | locked、adaptive两个字段路径列表；不能交叉声明同一属性 |
| responsive | {modeId,overrides}数组，每个mode最多一项 |
| source | 提取／编写／推断证据，来源节点和观测边界；可为null |
| decisionRefs | 当前节点使用的rules.decisions ID |
| extensions | 仅容纳有文档化语义的特殊属性，不用于藏另一套布局 |
| children | 唯一有序节点结构；responsive覆盖不得修改它 |

每个页面创建新节点时分配稳定ID，保留来源ID映射。不要使用会随前面节点增删而全部移动的纯遍历序号作为长期身份。

## 6. layout、sizing、placement

Flex：type=flex、direction、wrap、justify、align、gap、padding。padding顺序上右下左。Grid：type=grid、columns轨道、rowGap、columnGap、padding；每轨道mode=fixed/fraction/content，value按mode解释。Overlay：type=overlay、padding，子项需有明确锚定理由。

width/height的mode：

- fixed：value为固定逻辑长度。
- content：value=null，由内容和padding决定，受min/max约束。
- fill：value=null，填充父级分配区域。
- fraction：value为正权重，参与当前轴剩余空间分配。
- percent：value为0到1，分母为父内容区域相应尺寸。
- viewport：value=null，使用profile定义的可用窗口区域。

null的min/max表示未施加约束，不等于0。fixed、fraction、percent必须有数值；其他mode不得携带第二套固定值。min不得大于max。字体尺寸不使用几何值等比缩放。

placement包含mode=flow/anchored/fixed/sticky、anchorId、insets、zIndex、grow、shrink、basis、gridArea。flow不使用anchorId或insets。anchored/fixed必须有锚点；$viewport是允许的特殊锚点。sticky的anchorId指滚动容器并明确阈值。引用不得循环。anchor目标不是用于重新读取来源坐标。

Grid自动行序由children顺序决定；显式gridArea记录row、column、rowSpan、columnSpan。不能在同一个mode下既保留手写行容器树又隐式生成另一套网格。

## 7. responsive与锁定

base为node本体。匹配某个profile mode后，将该节点的唯一override递归替换到base；数组整项替换，不按索引合并。对象的type发生变化时整对象替换，不把Flex的字段遗留到Grid或另一种content中。没有显式覆盖的字段保持base值。

允许覆盖layout、sizing、placement、overflow、styleRef、content；禁止覆盖id、parentId、children、source、profile身份。跨条件需要完全不同信息架构时另建document。

policy.locked/adaptive是节点字段路径，如layout.padding、sizing.width。locked路径及其子路径不能被responsive覆盖；adaptive列出允许被mode覆盖的字段路径；未列入的字段不能被条件覆盖。locked锁定JSON规则本身，例如fill规则仍按父级空间计算实际宽度。两列表中相同或祖先／后代路径冲突时校验失败。环境字体缩放属于profile解释，不需要复制多个字号树。

## 8. library与内容

library.styles是样式ID到完整视觉配方的映射：

- fills：有序填充层；solid=color，linear-gradient=angle+stops，image=assetRef+fit。
- stroke：边宽数组、color、alignment，或null；radii按左上右上右下左下。
- effects：有序结构化效果，记录type与parameters；特殊效果需在生成的UI规范定义parameters语义。
- opacity：0到1。
- typography：字体家族、字号、字重、行高、字距、对齐，或null；字号、字距和长度型行高使用logical-px，倍数型行高使用倍率。
- extensions：仅用于有明确定义、当前基础模型未直接覆盖的视觉数据。不能以“暂不支持”静默移除。

library.assets中每项包含kind=image/vector/font、file或embedded、sha256、availability=available/missing/remote-unverified、critical。file相对包根且需要实际存在；embedded包含完整几何／数据，不能只有旧设计文件的节点链接。没有本地文件或内嵌内容时不能标available。

content按kind对应：

- text：固定文案使用value字符串；动态内容使用value=null及binding。两者共享wrap=wrap/nowrap、overflow=visible/truncate/scroll、maxLines或null、scaleWithSystem，按下节解释。
- image：assetRef、fit=contain/cover/stretch、focus两个0到1数值。
- vector：assetRef；图形内部节点不参与页面布局。
- container/shape：content=null，shape由视觉配方绘制。

source包含sourceId、nodeId或null、evidence=extracted/authored/inferred、referenceBounds或null。观测坐标只能用于审计，不能覆盖layout/sizing/placement。没有来源的规范制定容器可以source=null并通过decisionRefs说明。

semantics可以明确缺失；visual-only规范不因缺少业务动作而自动补需求。影响本次目标的关键缺失才进入critical issue。

### 8.1 固定文案与动态占位

先按内容用途区分，不按是否包含数字判定：

| 内容 | JSON表达 | 对齐标准 |
| --- | --- | --- |
| 页面功能标题、字段标签、按钮、选项、状态标签及说明文案 | content.value保存固定文字，binding省略或为null | 核对固定文字、视觉样式及结构 |
| 名称、用户输入、日期、时间、计数、金额、比例等示例数据 | content.value=null；binding保存展示模板及参数 | 核对绑定含义、格式和传入数据的呈现，不核对设计稿示例值 |
| 固定句式中的动态部分 | template保留固定文字，仅参数使用占位 | 同时核对固定部分与参数解析结果 |
| 图形呈现的数据量，例如进度填充比例 | 对应percent尺寸使用value=null和数值binding | 按传入比例计算尺寸，轨道、颜色、高度等仍按样式规范 |

静态的“截止日期”标签不能占位化；示例任务名称即使出现在页头，也使用占位。选中、只读、错误等已捕获视觉状态仍需严格验收，不能整段替换为任意文字而丢失状态语义。原稿中的具体值保留于来源留档，不作为binding默认值或回退值。节点name、document.title和来源元数据只用于识别，不是显示数据的备份。

文本示例：

~~~json
{
  "type": "text",
  "value": null,
  "binding": {
    "template": "截止日期：{{task.deadline}}",
    "parameters": {
      "task.deadline": {"type": "date", "format": "yyyy年M月d日"}
    }
  },
  "wrap": "wrap",
  "overflow": "visible",
  "maxLines": null,
  "scaleWithSystem": true
}
~~~

- binding.template中的占位写作{{字段路径}}；路径由英文字母开头的字母数字段组成，段之间用点连接。字段是展示输入契约，不据此推断接口、存储模型或业务算法。
- parameters逐一声明所有占位的type和format；重复使用同一占位只声明一次。未声明、未使用、空模板、残缺花括号及可执行表达式均不通过。
- string使用plain；integer使用0；number使用0.##或0%；date使用yyyy-MM-dd、yyyy年M月d日、M月d日、yyyy年M月、M月d日 EEEE；datetime使用yyyy-MM-dd HH:mm或M月d日 HH:mm；time使用HH:mm。0%将0到1的比例显示为百分数，0.##最多两位小数；EEEE按当前locale显示星期全名。日期、时间输入和时区由场景明确，不从图片中猜测运行时间。
- 解析后再测量文字。传入值可以改变换行和内容高度；不能将{{...}}本身作为应用最终显示文字。缺少参数、类型或格式不匹配时，验收输入未就绪，不能偷偷使用设计稿值通过验收。
- policy.locked锁定模板、格式和样式规则，不锁定外部传入值；数据替换不需要responsive mode。改变模板或视觉结构则修改正式JSON。

数值占位示例：

~~~json
{
  "mode": "percent",
  "value": null,
  "min": null,
  "max": null,
  "binding": {"path": "weekly.progressRatio", "type": "number", "min": 0, "max": 1}
}
~~~

本契约仅允许percent尺寸使用该数值binding。输入是0到1的比例，乘以父级内容尺寸；value与有效binding互斥。颜色、固定图标及普通布局尺寸不能仅因存在示例数据而占位化。binding=null可用于显式移除覆盖前的绑定。

基准视觉检查记录实际传入数据，以同一组数据生成预期与实际画面；动态文本及图形按解析结果比较。同一数量的文字与图形使用语义一致的数据；计算口径由正式需求或场景输入约定，不从原稿示例推断业务算法。适配检查另使用短文本、长文本及允许的边界值。若需跨页跟踪同一对象，场景给出同一输入或字段映射，不用设计稿中恰好相同或不同的值证明业务连续性。列表节点用于描述已捕获的行样式与状态组合，不能由示例计数推断正式业务数量或另造增删规则。

## 9. 校验边界

校验器检查：Schema子集、文件范围、清单hash、ID/父子/引用、组件/样式/资源、mode互斥、响应式覆盖、单一layout、定位锚点、尺寸、动态占位完整性与关键issue。它不会计算真实Flex/Grid布局，不会证明没有视觉溢出，也不会替代图形渲染或字体可用性检查。

结构通过与canonical就绪度分别报告。draft允许保留未解决问题；canonical遇到critical open issue、缺少可分类页面或关键缺失资源时发布就绪度为blocked，CLI以非零退出；结构结果仍独立报告。视觉not-tested不能升级为passed。

Skill自身不存放某次运行产物或验证日志。需要工作证据时写入本次输出目录的validation-report.json，并在来源／规范改变后重新校验。
