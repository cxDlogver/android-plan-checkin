# 当前项目UI分析与JSON对齐规范

版本：2.0.0；分析日期：2026-10-26；适用Skill：[ui-spec-normalizer](../skill/ui-spec-normalizer/SKILL.md)。

当前交付为draft：结构校验通过，Inter字体尚缺，基准视觉与响应式视觉均未执行。完整问题与状态以[manifest.json](manifest.json)和[validation-report.json](validation-report.json)为准。草稿可用于结构评审；补齐关键字体并复验后才能作为正式视觉基准发布。

## 1. 本次结论与来源

- 23个页面均为393逻辑像素宽，按768断点全部归mobile。没有desktop页面，不生成桌面版，也不将手机稿放大作为桌面依据。
- 2个组件分别为353×48和393×70，继承mobile。1860×220的方案概览属于reference，其宽度不参与端型判断。
- 读取984个原生节点：435个frame、405个text、119个icon、25个rectangle。全部原生容器为一维流；当前参考布局未报告裁剪问题。
- 规范化后为1003个节点：新增23个窗口容器，月历将5个周行合并为1个日期Grid，其余节点保留。容器最终为452个Flex、2个Grid、0个Overlay，普通布局定位全部使用flow。
- 405个文字节点保留：239处固定文案，166处数据内容转换为动态占位；119个图标使用26份去重SVG，视觉值归并为92套style。组件实例保留25处componentRef，采用展开快照。
- 本次主要读取plan/source-resource/ui/ui.pen，且仅通过pen.dev MCP读取；HTML用于核对节点顺序与提取SVG。逐页原生节点名称及顺序与对应HTML全部一致。
- PNG只审阅了02、04、11、17四份代表样例；未执行JSON渲染结果与原图的视觉差异测试。PNG的2倍导出尺寸不用于分类。
- 已复读26个画板并保留来源身份；当前JSON在来源结构上将示例数据归一化为动态占位。分析范围限定在plan/source-resource/ui。

来源身份、观测时间和节点内容指纹保存在manifest.sources；逐节点来源映射保存在source字段。最终对齐使用documents、rules和library，原始观测坐标不参与布局。

## 2. 页面与结构清单

下表宽高均为原生逻辑尺寸。长画板保留其参考高度；运行时页面高度取实际可用窗口，正文区域负责滚动。

| 标题与JSON | 类型 | 逻辑宽×高 | 源节点数 |
| --- | --- | --- | --- |
| [01-今日](documents/01-今日.json) | screen | 393×852 | 35 |
| [02-今日](documents/02-今日.json) | screen | 393×1140 | 80 |
| [03-计划](documents/03-计划.json) | screen | 393×852 | 46 |
| [04-新建计划](documents/04-新建计划.json) | screen | 393×1040 | 57 |
| [05-新建计划](documents/05-新建计划.json) | screen | 393×940 | 51 |
| [06-新建任务](documents/06-新建任务.json) | screen | 393×852 | 39 |
| [07-记录今天](documents/07-记录今天.json) | screen | 393×852 | 33 |
| [08-记录今天](documents/08-记录今天.json) | screen | 393×852 | 33 |
| [09-当日修改记录](documents/09-当日修改记录.json) | screen | 393×852 | 35 |
| [10-补记](documents/10-补记.json) | screen | 393×852 | 32 |
| [11-日历](documents/11-日历.json) | screen | 393×1100 | 152 |
| [12-晨间阅读](documents/12-晨间阅读.json) | screen | 393×852 | 41 |
| [13-运动](documents/13-运动.json) | screen | 393×852 | 42 |
| [14-提交报名材料](documents/14-提交报名材料.json) | screen | 393×852 | 33 |
| [15-编辑计划](documents/15-编辑计划.json) | screen | 393×852 | 37 |
| [16-计划管理](documents/16-计划管理.json) | screen | 393×852 | 30 |
| [17-删除并归档确认](documents/17-删除并归档确认.json) | screen | 393×852 | 25 |
| [18-归档后永久删除确认](documents/18-归档后永久删除确认.json) | screen | 393×852 | 24 |
| [19-本机设置](documents/19-本机设置.json) | screen | 393×852 | 27 |
| [20-记录暂未保存](documents/20-记录暂未保存.json) | screen | 393×852 | 29 |
| [21-登记完成](documents/21-登记完成.json) | screen | 393×852 | 29 |
| [22-记录详情](documents/22-记录详情.json) | screen | 393×852 | 29 |
| [23-跨日重新确认](documents/23-跨日重新确认.json) | screen | 393×852 | 29 |
| [Android V1-方案概览](documents/Android V1-方案概览.json) | reference | 1860×220 | 4 |
| [组件-三入口导航](documents/组件-三入口导航.json) | component | 393×70 | 10 |
| [组件-主要按钮](documents/组件-主要按钮.json) | component | 353×48 | 2 |

同名页面通过序号及原生ID区分。每个页面的状态来自源metadata.screenKey；该值标识当前视觉样例，不补充业务状态机或数据需求。

## 3. 本项目的尺寸、样式与响应式规则

以下“原稿”是提取事实，“规范化”是本次确定的执行规则。所有几何与字号使用logical-px。

| 部位 | 原稿中的明确值 | 当前JSON唯一规则 |
| --- | --- | --- |
| 窗口与手机画布 | 页面宽393 | 新增窗口Flex，宽高viewport；内部画布宽fill、max=480，居中，高fill。480是阅读限宽，不是第三类端型；W>=768时缺少desktop，不回退手机稿 |
| 页头 | 高92；padding=[8,20,12,20]；行间gap=3 | content高度，min=92；标题换行可增高。标题行gap=12；触控框固定宽48、最小高48，22大小的标题图标保持原值 |
| 正文 | padding=[12,20,20,20]；gap=16；宽高fill_container | 横向填充画布，扣除两侧20；纵向填充剩余区域，overflow.y=scroll。子项不压缩，不把保存按钮改成吸底按钮 |
| 内容卡片 | 多数padding=16；各卡片gap与视觉配方不同 | 宽度fill，高度content；padding、gap按每节点JSON原值保存，不把24内边距的空态卡片改成16 |
| 主按钮、普通选择项 | 主按钮高48；二、三、七等分组 | 高度content、min=48；横向fill_container转为fraction=1，等权分配。标签可换行，不缩字号。固定尺寸触控图标不参与文字分配 |
| 底导航 | 三等分、基准高70、图标20 | 容器及入口content、min=70，标签放大时可撑高；仍在正文滚动区外。缺少导航的页面不补导航 |
| 文字 | Noto Sans SC为主；日期等使用Inter；字重、字号逐节点不同 | styleRef保存基准字体和字重。业务文字按分配宽度换行，横向文字允许shrink=1，高度content。fontScale放大时重排；宽度变化不缩放字号 |
| 图标 | 状态图标14、导航20、页头22，另有提示图标 | 精确尺寸保存在各节点fixed宽高；SVG保存完整几何和颜色。图标不随画布等比缩放 |
| 环境区域 | 上部36、底部24，底部手势条100×4 | 标为环境托管；参考环境使用上述值，实际宿主只处理一次insets。样例系统时间、信号图标和手势条不由业务重复绘制 |
| 进度条 | 02、13页轨道321、填充203.333333 | 高6；填充宽percent使用weekly.progressRatio数值占位（0到1），按传入比例乘父轨道内容宽度。不固定为原稿203.333333/321 |

画布宽B=min(W,480)。正文可用宽度=B-40；普通padding=16的卡片内部宽度=B-72。等权横向组先扣除padding、固定项与gap，再按fraction分配剩余宽度。

例如W=393时，正文宽353、普通卡片内部宽321；W=320时分别为280、248。W=767时画布宽480，左右空余各143.5；跨到768后应选择desktop，而该设计尚未提供。

当前modes为空：单列结构、等分组和七列日历可由现有计算规则表达，不新增未经来源支持的布局切换点。固定JSON规则不随宽度改写，规则计算出的实际尺寸可以变化。后续若增加类内断点，必须在rules登记互斥条件，在节点policy.adaptive登记允许覆盖的字段，再指定responsive目标值。

### 日历唯一结构

11-日历的月历头部与日期区域保留在同一卡片内。星期为7列Grid；日期为7列×5行Grid，按原日期顺序自动排放，不保留Flex周行备选。

- 月历外壳padding=[16,2,16,2]。
- 星期与日期均为7个fraction=1的列，列距2。
- 日期Grid行距12；日期格高度content、min=48，字体放大可增高。
- 393宽时，月历内部宽349，每列宽=(349-6×2)/7≈48.143。
- 日期、月份和进度计数使用动态占位；选中描边、今天底色和各进度下标的视觉模式逐节点保留。场景输入须与这些展示角色匹配，不能根据原稿数字或颜色补出业务算法。

对应节点为n-MVcOd、n-ypuLU、n-MVcOd-dates，5个来源周行的ID与合并依据记录在rules.decisions.calendar-grid。

### 严格保留的视觉内容

颜色、渐变各stop、圆角、描边、阴影顺序、字体家族、基准字号和字重，全部取library.styles；不能按“整体看起来相近”统一为一个按钮或卡片样式。

背景主色#E8ECF0、文字#17212B、主色#263440、边框#ABB6C1等视觉值保存在library.styles。节点仍以自身styleRef为准，不能仅凭变量名覆盖具体状态颜色。本次保留了金属渐变及渐变描边，没有把它们降级为纯色。

### 固定文案与动态数据

固定的页面功能标题、标签、按钮、结果选项、状态说明及视觉配方按JSON严格对齐。任务名称、计划名称、日期、时间、备注、计数、统计比例与版本号使用动态占位；名称出现在页头时也不例外。原截图中的实际字符仅作来源留档。

文本节点的content.value=null时，binding.template使用{{字段路径}}，parameters声明每个字段的type和format。例如“截止日期：{{task.deadline}}”，task.deadline为date、格式yyyy年M月d日。参数不保存设计稿默认值。该字段是展示输入，不要求存在同名接口或存储字段。完整类型、格式及解析规则以[节点契约8.1](../skill/ui-spec-normalizer/references/node-contract.md#81-固定文案与动态占位)为准。

本包166个文字节点使用文本绑定，另有2个进度填充使用sizing.width.binding={path:weekly.progressRatio,type:number,min:0,max:1}和value=null。不同模板可以使用同一字段的不同格式；同一对象跨页浏览时，由同一场景数据传入名称、日期等值，不再加载各原图的具体示例数值。原图数据差异不作为迁移冲突，也不自动豁免真实数据连续性。

视觉验收先固定本次数据，再用同一输入解析预期界面与实际界面；比较固定文字、字段格式、布局、换行、样式及选中状态。动态值不与原图逐字匹配，不要求日期、数量、名称或进度回到原图示例。缺值或类型不符时输入未就绪；禁止把占位表达式直接显示到应用、以原图值兜底或缩小字体填入原文字宽度。长文案和边界值按现有适配规则验收。

## 4. JSON入口与节点解释

| 文件／字段 | 用途和含义 |
| --- | --- |
| manifest.json | 唯一document清单、来源版本、文件SHA-256、草稿状态、问题与视觉验证状态 |
| rules.json | 固定768分类、mobile环境、已确定决策和待执行的适配矩阵 |
| library.json | 92套视觉配方及字体、SVG资源；文档的styleRef和assetRef都在此解析 |
| documents/具体标题.json | 每页完整树；referenceSize为源逻辑宽高，profileId为mobile |
| id、parentId、children | 稳定身份、父关系、有序子树；不能依截图观测坐标重建另一棵树 |
| componentRef | 原生组件身份关联；本版展开快照完整保存当前实例，不运行时二次继承 |
| variant | 已捕获视觉样例的state及属性；不代表额外业务需求 |
| layout | 该容器唯一Flex／Grid结构；不存在候选列表 |
| sizing | 每轴一种{mode,value,min,max}；percent可使用value=null与binding传入数据比例，其余尺寸策略按节点确定 |
| placement | flow及Flex主轴grow/shrink/basis；本包无业务绝对定位，source坐标不参与布局 |
| overflow | 指定裁剪和滚动归属；23个页面的正文都是scroll |
| styleRef、content | 视觉配方及内容；固定文字使用value，动态文字使用value=null和binding，文字策略继续按wrap等字段执行 |
| policy、responsive | 当前规则锁定、adaptive与responsive为空；锁定模板和计算规则，不锁定binding的外部传入值 |
| ownership | application表示应用绘制；platform表示环境托管区域，不记录操作系统或运行平台类型 |
| semantics | 当前没有来源证明的业务动作与读屏语义为null，不猜测actionRef |
| source、decisionRefs | 审计来源及制定依据。source可为null的新增窗口/Grid使用normalized决策说明 |

完整字段及递归合并规则见[节点契约](../skill/ui-spec-normalizer/references/node-contract.md)，Schema副本见[schema/ui-spec.schema.json](schema/ui-spec.schema.json)。

## 5. 本包extension的确定含义

扩展只补充基础Schema不能完整表达的视觉与环境信息，不存候选布局。

- style.extensions.fontAssetRef：关联字体资源，fontFamilies仍为准确家族名称。Noto Sans SC文件随包保存；Inter目前missing，不能静默替换家族并宣称还原完成。
- style.extensions.strokePaint：渐变描边的唯一配方；保存widths、alignment、有序paints及geometry。出现该扩展时style.stroke=null，避免绘制两道边框。
- style.extensions.fillGeometry：按layer对应fills中的渐变层，保存归一化center、size与rotationCCW；用于保持源渐变在不同宽高比下的方向、长度和stop位置。
- node.extensions.textFlow：breakPolicy=grapheme表示按字素边界换行；maxWidth=allocated-parent-content表示内容宽度不超过父级给出的可用区域。原稿auto文本在空间足够时保持自然宽度，空间不足时按此规则重排。
- node.extensions.environmentRegion：声明top／bottom环境区的参考高度及宿主处理规则。样例绘制与宿主insets二选一，不重复叠加。
- node.extensions.sourceMetadata与iconIdentity：只记录样例来源和图标身份；实际矢量内容由assetRef解析，不能根据图标名字联网重取。
- profile.extensions.supportedWidth：本轮计划验证320 <= W < 768；低于320未纳入已声明的适配范围。分类规则仍是W<768为mobile。
- profile.extensions.validationCasesStatus：planned-not-executed表示矩阵已定义，尚未实际渲染测试。

渐变几何按当前节点几何盒计算。设宽高为w、h，center为(cx,cy)，rotationCCW为r，size第二项为k，则C=(cx×w,cy×h)，V=(-sin(r)×w×k,-cos(r)×h×k)。渐变stop沿C-V/2到C+V/2分布；size第一项在线性渐变中不改变长度。核心angle表示归一化方向，不能忽略fillGeometry而直接把它当成任意宽高比下的CSS角度。

所有尺寸与padding以几何盒为基准，描边按inner／center／outer绘制，阴影不改变布局分配。effects按数组保持前后层次，shadow.parameters包含shadowType、offset、blur、color、blendMode；缺省blur为0。本轮尚未通过真实渲染验证这些效果的最终合成。

## 6. 已知差异与发布限制

| 问题 | 本次处理 | 对交付的影响 |
| --- | --- | --- |
| FONT-INTER | 当前规范中Inter资源仍为missing；此前本地检索及远程读取未取得可用文件。本轮保留准确家族，不扩展下载任务 | 关键缺失，manifest保持draft、readiness=blocked；日历日期及汇总的字形尚无法自足 |
| PROGRESS-LABEL-GEOMETRY | 原文案与几何均已改为动态占位 | 已解决；按本次场景提供的计数和比例验收，不固定原稿数值 |
| DESKTOP-NOT-PROVIDED | 不生成desktop profile | 桌面端未覆盖；不能把768测试为“手机稿继续正常显示” |
| 未执行的视觉检查 | baselineVisual与responsiveVisual均为not-tested | 结构通过不代表页面已达到视觉还原或适配验收 |

本轮复核的原生布局在各参考尺寸下未报告裁剪；窄屏、长文案、键盘或字体放大后的视觉结果仍未验证。

## 7. 校验、验收与维护

已执行的结构检查：Schema与文件哈希、26份文档、1003个节点的ID/父子/引用、组件关联、样式与资源、单一布局、滚动和定位。覆盖检查确认405个文字节点及字体家族保留，26份SVG可解析，35个日期格完整；166个文本绑定与2个比例绑定通过占位契约检查。结论汇总在[校验报告](validation-report.json)。校验器仅读取规范包，不读取.pen、旧HTML或PNG。

待执行的视觉矩阵：宽320/360/393/480/767；高600/852及键盘压缩样例500；fontScale=1/1.3。参考图对照使用每页referenceSize；统一运行视口393×852另测长页滚动。767应选择mobile，768应判为未提供的desktop。长文案和字体放大应增加行数、增高内容并通过正文滚动，禁止整体缩放页面。

重新校验：

```text
python plan/skill/ui-spec-normalizer/scripts/validate_spec.py plan/ui-spec --report plan/ui-spec/validation-report.json
```

日常修改documents/rules/library后更新manifest哈希并复验。补齐Inter后登记文件哈希、解决FONT-INTER，再检查发布就绪度；不能只改authority隐藏缺失。

最终交付保留UI规范、manifest/rules/library、documents、Schema、校验报告及直接依赖的资源。原始节点快照副本、临时转换／审计脚本和过程记录在收尾时删除；来源与检查结论保存在最终字段和报告中。新增设计版本另行读取授权来源并明确迁移范围。

本次未修改应用实现、未生成业务实现计划、未执行实际应用视觉验收。
