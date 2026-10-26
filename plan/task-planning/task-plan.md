# UI-001 设计还原 · 文件级任务计划

执行状态：任务 通过 3、证据已失效 2、待实施 3；用例 未执行 135。本文由 task-plan.json 生成。

原子需求 129 项；补充用例 6 项；最少 211 次逻辑用例访问，其中重复 76 次。

[Test Case 图](test-cases.html) · [Test Case JSON](test-cases.json) · [任务 JSON](task-plan.json)

## 输入依据

- stateGraph：[../requirement-analysis/state-transitions.json](../requirement-analysis/state-transitions.json)，canonical SHA-256 040e0dd7b1c825b19221dd99e50e922a48b4e437aa093e3657ea5d56976e6d41
- atomicGraph：[../requirement-analysis/atomic-requirements.json](../requirement-analysis/atomic-requirements.json)，canonical SHA-256 61023ecfe33deff7dd8479466dc2df4d49abcff45ba72f9916bdd1b762b88adb
- 本轮范围与验收：[../source-resource/prd/设计还原需求文档.md](../source-resource/prd/设计还原需求文档.md) · $ · SHA-256 59323589edca8e6583e91a6b54f60ff9241ba016a57f90bc63430f817cfe77ab
- UI清单与就绪度：[../ui-spec/manifest.json](../ui-spec/manifest.json) · $ · SHA-256 12a18cbdd0988e0d76608757eecad4cacf1dfc4521d47bd13399b3893d52af81
- 适配规则与环境矩阵：[../ui-spec/rules.json](../ui-spec/rules.json) · $ · SHA-256 a61907f7416d59485c6d1648ed2c9796976160e77663704ca79a362559a20367
- 视觉配方与资源：[../ui-spec/library.json](../ui-spec/library.json) · $ · SHA-256 54ceeefcc112726efe4ec32f942ff9520bc19c683c59141bda266619d47ef522
- 节点及动态占位语义：[../ui-spec/UI规范.md](../ui-spec/UI规范.md) · $ · SHA-256 e360fd35ea24b35056cdf8e00fcce62c1efa8ee70f2c5a8c2c25dedf7d268ff5

## 执行前置项

- **READY-INTER · ready**：正式UI资料中的Inter 4.1字体及OFL许可已登记。
  补足标准：P02使用library登记文件并核对原始SHA-256，实际字形仍按原生视觉项验收。
  影响用例：TC-G-LAYOUT、TC-G-VISUAL、TC-T002、TC-T005、TC-T006、TC-T012、TC-T013、TC-T017、TC-T020、TC-T095、TC-T096、TC-T099、TC-T109、TC-T119、TC-T124
- **READY-UI-HARNESS · missing**：本轮用例所需的界面测试入口、预期计算和取证设施尚待建立。
  补足标准：P01建立计划中的Node/原生测试入口和独立oracle；P03-P07提供真实视图及浏览控制器后才运行相关用例，不把本轮规划校验当产品测试。
  影响用例：TC-T001～TC-T129（连续ID）、TC-G-VISUAL、TC-G-LAYOUT、TC-G-SCOPE、TC-G-EVIDENCE、TC-REG-CONTROLS、TC-REG-CONTAINERS
- **READY-NATIVE-HOST · missing**：本轮尚未启动并验证隔离开发应用及原生测试环境。
  补足标准：执行前确认开发包、指定隔离设备、Appium会话与测量能力，按rules提供逻辑窗口/fontScale/insets/键盘输入；只操作隔离开发宿主，不读取旧验收报告。
  影响用例：TC-G-LAYOUT、TC-G-VISUAL、TC-REG-CONTAINERS、TC-REG-CONTROLS、TC-T001～TC-T129（连续ID）

## 代码链路证据

- C-ROOT：[../../app/_layout.tsx](../../app/_layout.tsx) · L9-L13；字体加载、SafeAreaProvider及现有业务Provider挂载；SHA-256 fffd916f56239a0528d3c30dbf61ab1969245c9bd9244182bcf6c330e26c9e8f
- C-TABS：[../../app/(tabs)/_layout.tsx](../../app/(tabs)/_layout.tsx) · L5-L7；导航外观与clearPins事件；SHA-256 4d62f82bbf02377740aa4306aa1c92c80bb0d55ac110c7ed1fb358093b8e9bf3
- C-METAL：[../../src/ui/metal.tsx](../../src/ui/metal.tsx) · L9-L20；公共配方、Button/Choice/Field事件与Page安全区/键盘/滚动；SHA-256 3aa96a76b3e18622d40fba5e297b5dd3664b7bdbb4c7fad7bac824c81e8be16e
- C-DATEFIELD：[../../src/ui/metal.tsx](../../src/ui/metal.tsx) · L21-L24；存量日期控件局部行为；本轮不设计展开视图；SHA-256 3aa96a76b3e18622d40fba5e297b5dd3664b7bdbb4c7fad7bac824c81e8be16e
- C-TODAY：[../../src/features/today.tsx](../../src/features/today.tsx) · L10-L22；今日投影、列表呈现与记录/新建事件；SHA-256 49513b025a3207a14fd727810b03a89e56d7e78591e94c2173ad10b2dfe455e2
- C-PLANS：[../../src/features/plans.tsx](../../src/features/plans.tsx) · L10-L17；计划列表、筛选、分页与详情事件；SHA-256 a9d90b1c3be83667f323828f2bf90793505a653ad2a48b6bb2d1ee89febe027e
- C-CALENDAR：[../../src/features/calendar.tsx](../../src/features/calendar.tsx) · L9-L24；日历投影与选中日期、宽度计算和测量；SHA-256 a0a7fff912af7cbd494f94028354390bcf3c14c0844ec25f2ac98da8ea3bfe85
- C-PLANFORM：[../../src/features/plan-form.tsx](../../src/features/plan-form.tsx) · L11-L44；计划表单状态及新建/编辑提交和路由；SHA-256 3376d44f0955e2ed120ff4ecf765b35cef52358b4dda2a30c3138497197ac056
- C-RECORDFORM：[../../src/features/record-form.tsx](../../src/features/record-form.tsx) · L12-L35；记录表单输入、冻结Envelope与提交结果；SHA-256 6098b3eb174c27f3436be26dfcedb6be170da73cffe456abc2378d0e5a3b7650
- C-RECORDTAIL：[../../src/features/record-form.tsx](../../src/features/record-form.tsx) · L40；记录视图、重确认及保存事件接线；SHA-256 6098b3eb174c27f3436be26dfcedb6be170da73cffe456abc2378d0e5a3b7650
- C-DETAIL：[../../src/features/plan-detail.tsx](../../src/features/plan-detail.tsx) · L13-L26；详情投影、历史分页与manage命令；SHA-256 397941db6e6f0c43305314ddff8e32d2772d2bf2def8c28ae71201e5d902e127
- C-SETTINGS：[../../src/features/settings.tsx](../../src/features/settings.tsx) · L1-L5；动态版本和本机设置说明；SHA-256 c4a7013dba704b559005dec21779afcddc48a5dd73770e982298ff7d35ca72cd
- C-SHARED：[../../src/features/shared.tsx](../../src/features/shared.tsx) · L8-L15；PlanCard及openRecord路由；SHA-256 83770c0b34c06226e10b597cab7c964a2f5db0a7ed06a6c24b4ed15f8b405da2
- C-DRAFT：[../../src/features/draft.ts](../../src/features/draft.ts) · L6-L17；dirty/busy返回保护；提取时保持hook；SHA-256 cac740799c3f21b6d6a1b4e21a272f4cf7d85f0f2962df13b1f3c7072777dcd6
- C-PROVIDER：[../../src/state/AppProvider.tsx](../../src/state/AppProvider.tsx) · L13-L26；现有命令、refresh和全局读错误边界；SHA-256 a652fc94df6454ba45fd33ff5b2d1b93c9b15d5bbda9d6ad322cd654b9921654
- C-SERVICE：[../../src/application/service.ts](../../src/application/service.ts) · L1-L12；命令/存储与快照边界；本轮保留；SHA-256 db9165efbe0e40d42b2f0c6113cb582a44ad8193ad4fd3fd9caf87a0e9fea5ef
- C-QUERY：[../../src/application/projections.ts](../../src/application/projections.ts) · L1-L12；投影和分页协议；本轮保留；SHA-256 76e83f2722dfd00fc3541bdba86711ca7f712bd4546c345861258356aba96b4a
- C-DB：[../../src/infrastructure/database/executor.ts](../../src/infrastructure/database/executor.ts) · L1-L12；SQLite边界；本轮不修改；SHA-256 8752b4ee196c34b517fe2657a1e48eabb05098c1b1ba4cdda4c7c033e1389839
- C-DEV：[../../src/verification/development.tsx](../../src/verification/development.tsx) · L15-L24；开发验证入口，UI浏览使用独立内存ctx；SHA-256 a288f0623f5e1a21aba5209ec578f60c08eb38518f7b8d00f034c14c89380ac1
- C-PRODUCTION：[../../src/verification/production.tsx](../../src/verification/production.tsx) · L1-L2；生产构建验证组件为空；SHA-256 7bebcb9cd9df0058283b4d22d8860133a394f38f8e53396c7ad22cc4ec34f159
- C-METRO：[../../metro.config.cjs](../../metro.config.cjs) · L8-L12；开发/生产验证模块解析分离；SHA-256 2629529b134c31a780131befce67ffce33cbecd8223433023cd7ba12373a8c87
- C-NATIVE：[../../app/native.tsx](../../app/native.tsx) · L1-L3；既有验证路由；SHA-256 939f8043989add9c40f9b26d71280d3e4e6f6859d8c8583f1cc857a999f9a28b
- C-PACKAGE：[../../package.json](../../package.json) · L1-L18；既有命令和依赖入口；SHA-256 1515d6b423e38d84dfee54588437af46c3661532cff51fe21447bff2b900cdf4
- C-TSC：[../../tsconfig.node.json](../../tsconfig.node.json) · L1-L15；Node单元测试编译范围不含UI；SHA-256 67baa569accbb53a6fd85506fdbc8b847da95b99753335029708c410aa23b0ef
- C-INTEGRATION：[../../tsconfig.integration.json](../../tsconfig.integration.json) · L1-L5；当前集成仅服务与数据库，不是组件宿主；SHA-256 14f3908b05d888b4023c21d49dc13480c66b21caf2e7feeae9eb30a189fe4f42
- C-DEVICE：[../../scripts/device-driver.cjs](../../scripts/device-driver.cjs) · L9-L21；既有隔离开发包设备会话、原生树与截图接口；SHA-256 f3475559da03cc8a0dda80ffd453f118ec5cd8f8632aec05d4d73a71c7c6d48d

## 直接影响与回归范围

- **I-CONTROLS · regression**：公共控件禁用、选中、受控输入和可访问属性保持
  机制：P02替换共享Button/Choice/Field的呈现层，若重组Pressable/TextInput时遗漏disabled、回调或属性透传，会直接改变多个存量页面事件。
  暴露输入：disabled/启用分别触发点击，Choice选择值与Field受控输入/alert的最小组件夹具。
  判断：主用例仅验收UI浏览，不足以证明所有存量控件公开props和禁用契约，补一个定向组件集成用例。
  用例：TC-REG-CONTROLS
- **I-CONTAINERS · regression**：生产容器的提交、返回、确认、草稿保护及列表/导航事件接线保持
  机制：P04-P06将JSX提取为props驱动视图，事件参数或调用方接线变化可绕过busy/dirty保护，或误把UI浏览保存路由用于生产容器。 列表/导航视图提取也可能遗漏clearPins、loadNext或日期选中事件，因此只核对这些公开事件的接线，不扩大到其内部算法。
  暴露输入：真实容器挂载新视图后的合法保存、取消确认、busy重复触发及dirty返回；观察原Envelope和router/confirm外部端口。 另触发tab事件、列表/历史加载更多、日历选中，观察clearPins、nextCursor及选中/过滤重置回调参数。
  判断：UI-only主路线不能验收存量业务容器事件契约；仅回归被本次提取直接触及的边界，不测试服务内部。
  用例：TC-REG-CONTAINERS
- **I-UI-ROUTE · covered**：既有视觉入口和返回上下文准确
  机制：控件与视图提取会影响点击目标与返回来源。
  暴露输入：Today/Plans两个表单入口、详情/记录返回和类型切换的全部主迁移。
  判断：已由129个主用例的初终态及returnContext检查覆盖，不另复制回归图节点。
  用例：TC-T001～TC-T129（连续ID）
- **I-DATA-CORE · unaffected**：存量服务、投影分页、日期/统计与SQLite事务保持
  机制：领域、服务、投影与存储文件保持不变；AppProvider只新增ContextValue及Context.Provider包装的导出作用域，不改变其初始化、value、refresh、execute和错误处理实现。UI浏览使用独立内存数据，组件回归通过新作用域注入完整Context。
  暴露输入：不建立额外输入；实施差异若触及这些模块须重新审查。
  判断：只增加测试注入出口不改变原业务行为，其他模块只读，未发现需要扩大到全业务矩阵的直接损害机制；若实际改动执行逻辑则重新审查。
  用例：无

## P01 · 建立本轮独立预期计算器与测试入口

使UI JSON和明确场景输入能够生成独立预期，并使Node及原生组件集成/视觉检查可按同一用例身份执行。

依赖：无

文件范围：

- modify [../../package.json](../../package.json)：增加本轮UI测试命令，保留既有test:domain
- read [../../tsconfig.node.json](../../tsconfig.node.json)：作为Node编译模式参考
- read [../../tsconfig.integration.json](../../tsconfig.integration.json)：确认现有集成范围，保留存量服务/DB测试
- read [../../scripts/device-driver.cjs](../../scripts/device-driver.cjs)：只复用底层设备访问，不读取旧resource/.artifacts报告
- create [../../tsconfig.ui-tests.json](../../tsconfig.ui-tests.json)：编译纯TS绑定/控制器/证据单元与集成测试
- create [../../tests/ui/oracle.ts](../../tests/ui/oracle.ts)：独立读取正式JSON/rules/library，计算文本/配方与布局约束预期
- create [../../tests/ui/fixtures.ts](../../tests/ui/fixtures.ts)：按用例dataProfiles解析场景上下文，提供固定边界与动态对象输入
- create [../../tests/ui/runner.cjs](../../tests/ui/runner.cjs)：按coverage.sequence管理given、handoff、restart与失败停止
- create [../../tests/ui/native-adapter.cjs](../../tests/ui/native-adapter.cjs)：实际原生事件、节点测量与证据收集；不使用浏览器
- create [../../src/verification/ui-test-host-development.tsx](../../src/verification/ui-test-host-development.tsx)：真实公共控件/容器集成的开发宿主及外部依赖注入
- create [../../scripts/ui-test.cjs](../../scripts/ui-test.cjs)：统一unit/integration/native与evidence入口，区分验证规划和执行产品
- modify [../../src/state/AppProvider.tsx](../../src/state/AppProvider.tsx)：仅导出类型与最小Context注入作用域，供开发组件测试提供内存端口；不改变AppProvider现有初始化/refresh/execute实现
- modify [../../src/verification/development.tsx](../../src/verification/development.tsx)：挂载本轮独立控件测试宿主入口；保留原有验证能力。
- create [../../tests/ui/harness.test.cjs](../../tests/ui/harness.test.cjs)：P01实现完成后编写基础设施脚本验收；复用同一进程覆盖协议、独立预期与记录器。

实施步骤：

1. 为纯TS测试复用当前Node --test及独立编译目录；组件集成在开发原生宿主挂载真实React Native组件和容器，只注入execute/router/confirm等外部端口，不用DOM快照冒充原生布局。 由于Metro排除tests目录，Node测试文件只通过native-adapter驱动开发宿主；真实组件和容器挂载代码放src/verification，禁止从应用直接导入tests。
2. 预期计算器读取正式JSON、rules、library和本次输入，禁止调用待实现的binding/浏览控制器求预期。构建接收nodeId与运行环境的测量适配器，原截图只供阅读来源。
3. 解析每个dataProfile字段的类型/格式；生成run.id相关名称/对象，捕获时钟/时区/版本；按语义角色关联实体，场景缺值即失败。分支响应在操作触发后按Mock约定交付并恢复。
4. 运行器按最优路线继承上下文或重新进入起点；每次访问均验收given和expected，失败停止。环境矩阵在专门用例内部执行，独立补充用例不向非起点提供fixture捷径。
5. 增加测试命令、证据格式校验和未执行状态保护。执行证据放在独立运行目录，不反写本规划的not_run为假通过。
6. 为现有私有Context增加只包装Context.Provider的导出作用域及ContextValue类型导出；开发组件宿主通过它提供完整内存Context与execute/queries spy，生产AppProvider继续使用原value和原初始化流程。路由/confirm替身在测试边界安装并恢复，不替换容器保存函数或草稿hook。

Test Case：TC-G-EVIDENCE、TC-G-LAYOUT、TC-G-SCOPE、TC-G-VISUAL、TC-REG-CONTAINERS、TC-REG-CONTROLS、TC-T001～TC-T129（连续ID）

原子需求：R-T001～R-T129（连续ID）

完成标准：

- Node入口可运行纯逻辑/协议测试；原生组件宿主可触发实际事件并返回原生树及测量。
- oracle与被测实现独立，证据含版本、节点、环境、输入、截图和差异；模拟结果与宿主结果明确区分。

任务状态：通过；计划检查：

- pnpm typecheck；前置任务：无；通过
- node scripts/ui-test.cjs unit --case TC-G-EVIDENCE；前置任务：P01；通过
- node scripts/ui-test.cjs integration --smoke；前置任务：P01；通过

## P02 · 还原共享视觉配方、字体与页面骨架

统一公共控件和宿主环境分工，使各页面复用同一份JSON配方，并保留公共组件现有事件契约。

依赖：P01

文件范围：

- modify [../../app/_layout.tsx](../../app/_layout.tsx)：按library挂载真实字体，安全区仅宿主承担一次
- modify [../../src/ui/metal.tsx](../../src/ui/metal.tsx)：替换外观与布局实现，保留Button/Choice/Field公开事件与可访问契约
- modify [../../app/(tabs)/_layout.tsx](../../app/(tabs)/_layout.tsx)：对齐导航组件实例并保留clearPins事件
- read [../../src/ui/metal.tsx](../../src/ui/metal.tsx)：读取日期控件交互边界，保留本轮未提供的展开实现
- create [../../src/ui/spec-tokens.ts](../../src/ui/spec-tokens.ts)：由当前library/rules落实配方映射，避免散落新常量
- create [../../src/ui/spec-icons.tsx](../../src/ui/spec-icons.tsx)：复用plan/ui-spec矢量资源并建立assetRef映射
- create [../../src/ui/bindings.ts](../../src/ui/bindings.ts)：按typed binding格式化传入值，必需值缺失即报告
- create [../../assets/fonts/NotoSansSC-VF.ttf](../../assets/fonts/NotoSansSC-VF.ttf)：从正式UI资产取得同哈希可变字体，不继续用不同文件冒充
- create [../../assets/fonts/Inter.ttf](../../assets/fonts/Inter.ttf)：资源就绪后纳入已核对版本/许可的Inter字体
- create [../../assets/fonts/Inter-LICENSE.txt](../../assets/fonts/Inter-LICENSE.txt)：保留与实际Inter资源一致的许可
- create [../../src/ui/spec-types.ts](../../src/ui/spec-types.ts)：定义确定节点、输入及呈现事件的应用类型。
- create [../../src/ui/spec-renderer.tsx](../../src/ui/spec-renderer.tsx)：用唯一React Native组件树落实JSON节点布局、样式和事件。
- create [../../src/ui/spec-documents.ts](../../src/ui/spec-documents.ts)：把正式JSON编译为应用只读呈现结构；测试从原JSON独立求预期。

实施步骤：

1. 从library的styleRef/assetRef落实颜色、字体、圆角、描边、渐变、阴影及矢量；固定逻辑尺寸不按窗口整体缩放。
2. 按唯一flow布局将页头/底导航置于主业务滚动区外，内容宽min(W,480)，宽度分类只有768；safe-area和键盘由宿主实际环境处理一次。
3. 保留Button/Choice/Field的disabled、onPress/onChange、testID、accessibilityState及alert行为；保留Page back入口和原有日期控件事件。
4. 字体先核对正式库哈希与许可；Inter缺失时保持对应验收阻碍，不静默替换。typed binding与比例尺寸采用传入数据，不使用原图默认值。

Test Case：TC-G-EVIDENCE、TC-G-LAYOUT、TC-G-SCOPE、TC-G-VISUAL、TC-REG-CONTAINERS、TC-REG-CONTROLS、TC-T001～TC-T129（连续ID）

原子需求：R-T001～R-T129（连续ID）

完成标准：

- 公共视觉配方与组件实例可逐节点对照正式JSON；每个容器只有一种布局。
- 直接受损控件契约的TC-REG-CONTROLS通过，字体资源未就绪时视觉项不通过。

任务状态：通过；计划检查：

- node scripts/ui-test.cjs unit --case TC-G-VISUAL；前置任务：P01、P02；通过
- node scripts/ui-test.cjs integration --case TC-REG-CONTROLS；前置任务：P01、P02；通过
- node scripts/ui-test.cjs native --case TC-G-LAYOUT；前置任务：P01、P02；通过

## P03 · 还原今日、计划与日历呈现视图

提取只接收展示输入及事件的真实视图；业务容器继续使用原投影，UI浏览宿主可复用同一视图。

依赖：P02

文件范围：

- modify [../../src/features/today.tsx](../../src/features/today.tsx)：提取可见树并透传现有投影与事件
- modify [../../src/features/plans.tsx](../../src/features/plans.tsx)：提取列表外观，保持filter/cursors查询逻辑
- modify [../../src/features/calendar.tsx](../../src/features/calendar.tsx)：呈现层改为JSON七列/35槽位场景规则与连续尺寸，保留生产月份投影和选择回调
- modify [../../src/features/shared.tsx](../../src/features/shared.tsx)：PlanCard接收可复用展示props，保留既有openRecord契约
- read [../../src/application/projections.ts](../../src/application/projections.ts)：读取既有投影/游标，保持文件不变
- create [../../src/ui/screens/TodayView.tsx](../../src/ui/screens/TodayView.tsx)：空/有计划今日视图
- create [../../src/ui/screens/PlansView.tsx](../../src/ui/screens/PlansView.tsx)：计划列表视图
- create [../../src/ui/screens/CalendarView.tsx](../../src/ui/screens/CalendarView.tsx)：同一七列布局组件接收日期槽位/选中态，UI场景35槽位与生产投影实际槽位由调用方提供

实施步骤：

1. 将JSX与呈现样式提取到纯视图，参数明确数据及onAction；视图不能调用useApp/execute。生产容器保留queries、pins、分页状态及原路由回调。
2. 对齐今日分组、计划卡片、列表按钮、底导航及日历七列布局；移除呈现层width<380档位，改为padding/gap/fraction连续适配。
3. UI浏览场景使用JSON35格及传入日期/计数，生产容器继续传原月份投影，不将固定35格约束强加给全部真实月份。单一CalendarView布局支持输入槽位数量，结构规则一致。
4. nodeId稳定映射到真实控件测试定位，点击项按语义角色解析实体，不依赖示例名称或第几条列表。

Test Case：TC-G-LAYOUT、TC-G-VISUAL、TC-REG-CONTAINERS、TC-T001～TC-T008（连续ID）、TC-T012～TC-T023（连续ID）、TC-T026、TC-T027、TC-T030、TC-T031、TC-T034、TC-T035、TC-T038、TC-T039、TC-T042、TC-T043、TC-T046～TC-T056（连续ID）、TC-T062、TC-T065、TC-T072、TC-T075、TC-T082、TC-T085、TC-T086、TC-T087、TC-T095、TC-T096、TC-T099、TC-T100、TC-T101、TC-T106、TC-T109、TC-T119、TC-T124

原子需求：R-T001～R-T008（连续ID）、R-T012～R-T023（连续ID）、R-T026、R-T027、R-T030、R-T031、R-T034、R-T035、R-T038、R-T039、R-T042、R-T043、R-T046～R-T056（连续ID）、R-T062、R-T065、R-T072、R-T075、R-T082、R-T085、R-T086、R-T087、R-T095、R-T096、R-T099、R-T100、R-T101、R-T106、R-T109、R-T119、R-T124

完成标准：

- 两类今日、计划、给定日历场景与动态输入吻合；同一视图用于生产容器和UI浏览。
- 查询/分页/记录权限算法文件不修改；提取前后回调参数契约保持。

任务状态：证据已失效；计划检查：

- node scripts/ui-test.cjs integration --local-task P03；前置任务：P01、P03；证据已失效
- node scripts/ui-test.cjs native --local-task P03；前置任务：P01、P03；证据已失效

## P04 · 还原新建与编辑表单

固定日期、每周和一次性表单按JSON显示，由调用方保持入口、草稿和提交语义。

依赖：P02

文件范围：

- modify [../../src/features/plan-form.tsx](../../src/features/plan-form.tsx)：提取显示部分，保留现有保存/Envelope/类型确认处理
- read [../../src/features/draft.ts](../../src/features/draft.ts)：保留dirty/busy返回保护
- create [../../src/ui/screens/PlanFormView.tsx](../../src/ui/screens/PlanFormView.tsx)：固定/每周/一次性/编辑表单的确定结构及onAction
- create [../../src/ui/plan-form-presentation.ts](../../src/ui/plan-form-presentation.ts)：将表单展示数据映射到对应视图；不改领域模型

实施步骤：

1. 保留PlanForm中的保存函数、frozen命令、revision、busy与useDraftGuard，将可见字段组和事件回调传入PlanFormView。
2. 按JSON对齐类型选择、固定标签、等权按钮、日期/备注输入和保存按钮在正文流的位置，动态字段从ctx或实际容器数据接收。
3. UI浏览切换类型只替换既有表单视图并保留sharedDraft/returnContext；生产容器继续使用原类型切换确认，不把本轮UI场景导航覆盖既有成功路由。

Test Case：TC-G-LAYOUT、TC-REG-CONTAINERS、TC-T003、TC-T009、TC-T021、TC-T024～TC-T047（连续ID）、TC-T088、TC-T089

原子需求：R-T003、R-T009、R-T021、R-T024～R-T047（连续ID）、R-T088、R-T089

完成标准：

- 同一表单视图能够接受不同数据且按JSON换行/增高；入口返回上下文无丢失。
- 存量新建成功进详情、编辑成功返回和dirty保护的原契约通过定向回归。

任务状态：证据已失效；计划检查：

- node scripts/ui-test.cjs integration --local-task P04；前置任务：P01、P04；证据已失效
- node scripts/ui-test.cjs native --local-task P04；前置任务：P01、P04；证据已失效

## P05 · 还原记录、详情与反馈画面

记录、补记、登记完成及两个异常反馈使用真实呈现组件，输入和分支来自明确上下文与端口。

依赖：P02

文件范围：

- modify [../../src/features/record-form.tsx](../../src/features/record-form.tsx)：保留原记录提交、权限与frozen命令，接入新视图
- read [../../src/features/record-form.tsx](../../src/features/record-form.tsx)：现有日期重确认/字段/按钮接线是提取的核对依据
- read [../../src/features/draft.ts](../../src/features/draft.ts)：保留原草稿保护
- create [../../src/ui/screens/RecordFormView.tsx](../../src/ui/screens/RecordFormView.tsx)：记录今天、修改/补记/完成及只读记录视图
- create [../../src/ui/screens/RecordFeedbackView.tsx](../../src/ui/screens/RecordFeedbackView.tsx)：未保存/日期变化的现有JSON视觉反馈，调用方控制动作
- create [../../src/ui/record-presentation.ts](../../src/ui/record-presentation.ts)：展示输入与固定状态语义映射

实施步骤：

1. 按document结构组织要做/不要做、已选结果、历史只读、原值与日期提示；固定文案与动态binding分开。
2. 容器继续执行原权限、命令和保存处理，新视图只发出事件；原异常码处理与本轮UI场景的outcome.screen由不同调用方映射到相同呈现组件。
3. not-saved重试、date-changed重新确认及普通返回按场景端口动作后结果切换；保留原草稿与对象，不注入真实存储异常或实际跨日。

Test Case：TC-G-LAYOUT、TC-REG-CONTAINERS、TC-T011～TC-T015（连续ID）、TC-T050～TC-T055（连续ID）、TC-T090～TC-T129（连续ID）

原子需求：R-T011～R-T015（连续ID）、R-T050～R-T055（连续ID）、R-T090～R-T129（连续ID）

完成标准：

- 六个条件迁移均有正确UI响应准备；不提前跳到终态，不丢输入。
- 只读和错误说明可见，容器原提交/返回/草稿功能通过回归。

任务状态：通过；计划检查：

- node scripts/ui-test.cjs integration --local-task P05；前置任务：P01、P05；通过
- node scripts/ui-test.cjs native --local-task P05；前置任务：P01、P05；通过

## P06 · 还原计划详情、管理、删除确认和设置

将详情/管理/确认/设置的可见标准落实为可复用视图，保留现有生产容器的命令与分页行为。

依赖：P02

文件范围：

- modify [../../src/features/plan-detail.tsx](../../src/features/plan-detail.tsx)：提取详情/管理呈现并保留manage与history分页
- modify [../../src/features/settings.tsx](../../src/features/settings.tsx)：设置说明和动态元信息按JSON对齐
- read [../../src/features/shared.tsx](../../src/features/shared.tsx)：读取既有记录路由与公共卡片契约
- create [../../src/ui/screens/PlanDetailView.tsx](../../src/ui/screens/PlanDetailView.tsx)：固定、每周及一次性详情
- create [../../src/ui/screens/PlanManagementView.tsx](../../src/ui/screens/PlanManagementView.tsx)：管理及两种删除确认的既有视觉结构
- create [../../src/ui/screens/SettingsView.tsx](../../src/ui/screens/SettingsView.tsx)：本机设置展示及版本输入

实施步骤：

1. 保留PlanDetail中的queries/history/manage命令处理与确认调用，提取展示数据和onAction；给UI浏览宿主提供不执行命令的场景端口。
2. 详情统计、历史、描述和版本只作为展示输入；不在本轮重算统计或改写数据库。
3. 确认页面按既有JSON呈现，在UI浏览中确认/取消返回对应视觉画面；生产容器的Alert确认与真正命令机制保留，不由场景图驱动。

Test Case：TC-G-VISUAL、TC-REG-CONTAINERS、TC-T004、TC-T007～TC-T011（连续ID）、TC-T018、TC-T022、TC-T023、TC-T048、TC-T049、TC-T056～TC-T094（连续ID）、TC-T097、TC-T098、TC-T110、TC-T111、TC-T116、TC-T120、TC-T122

原子需求：R-T004、R-T007～R-T011（连续ID）、R-T018、R-T022、R-T023、R-T048、R-T049、R-T056～R-T094（连续ID）、R-T097、R-T098、R-T110、R-T111、R-T116、R-T120、R-T122

完成标准：

- 固定/每周/一次性详情、管理、两种确认和设置均能用输入对齐JSON。
- 生产容器取消确认不发命令、busy防重及成功路由等原事件契约保留。

任务状态：待实施；计划检查：

- node scripts/ui-test.cjs integration --local-task P06；前置任务：P01、P06；未执行
- node scripts/ui-test.cjs native --local-task P06；前置任务：P01、P06；未执行

## P07 · 连接独立UI浏览宿主与完整视觉路线

通过真实控件连接已提供23屏，使用同一组呈现组件，严格隔离本轮视觉动作与生产业务效果。

依赖：P03～P06（连续ID）

文件范围：

- modify [../../src/verification/development.tsx](../../src/verification/development.tsx)：开发验证页增加UI浏览入口；不触发seed/execute
- read [../../src/verification/production.tsx](../../src/verification/production.tsx)：核对生产验证入口为空
- read [../../metro.config.cjs](../../metro.config.cjs)：核对开发模块不进入生产解析
- read [../../app/native.tsx](../../app/native.tsx)：复用既有开发验证路由
- create [../../src/verification/ui-review-development.tsx](../../src/verification/ui-review-development.tsx)：挂载共享视图及内存浏览控制器
- create [../../src/verification/ui-browse-model.ts](../../src/verification/ui-browse-model.ts)：纯TS的场景导航、returnContext与动作后UI响应消费
- create [../../src/verification/ui-data-context.ts](../../src/verification/ui-data-context.ts)：场景对象/草稿/环境映射与必需输入检查

实施步骤：

1. 实现只服务本轮UI浏览的纯TS控制器，使用正常控件事件与明确的场景状态；运行时不能直接读取测试状态图并返回其to作为实现。既有状态图仅作为测试预期和路线来源。
2. S01为起点，连接既有标签、详情、表单类型切换、管理及返回路径；保留不同入口的returnContext，不添加无JSON的月份、筛选展开和新结果。
3. 与生产容器复用P03-P06实际视图，禁止复制另一套UI树；浏览控制器只更新内存展示上下文，不调用execute、真实数据库seed或跨日逻辑。
4. record-response为外部UI场景端口，动作触发时消费ordinary-return/not-saved/date-changed，重试按已要求普通路径。所有其他确定动作不增加伪条件。
5. 验证宿主从现有开发验证页打开，生产verification为null并不导入新开发宿主；UI场景与生产容器路由语义分别验收。

Test Case：TC-G-SCOPE、TC-T001～TC-T129（连续ID）

原子需求：R-T001～R-T129（连续ID）

完成标准：

- 129个主用例的事件入口可触发真实呈现组件，沿既有最优路线合法可达。
- 写入/execute调用数为0；同对象动态输入一致，不将场景保存当实际业务成功。

任务状态：待实施；计划检查：

- node scripts/ui-test.cjs integration --primary-route；前置任务：P01、P07；未执行
- node scripts/ui-test.cjs integration --case TC-G-SCOPE；前置任务：P01、P07；未执行
- node scripts/ui-test.cjs native --primary-route；前置任务：P01、P07；未执行

## P08 · 建立直接影响回归并完成验收记录

针对公共控件及容器视图提取的明确风险执行回归，同时按最优路线收集本轮UI证据。

依赖：P07

文件范围：

- create [../../tests/ui/shared-controls.test.cjs](../../tests/ui/shared-controls.test.cjs)：TC-REG-CONTROLS真实公共组件集成
- create [../../tests/ui/container-boundary.test.cjs](../../tests/ui/container-boundary.test.cjs)：TC-REG-CONTAINERS真实容器与呈现视图集成
- create [../../tests/ui/bindings.test.ts](../../tests/ui/bindings.test.ts)：动态格式/缺值/比例边界单元测试
- create [../../tests/ui/evidence.test.ts](../../tests/ui/evidence.test.ts)：A07及not_run记录约束单元测试
- read [../../src/state/AppProvider.tsx](../../src/state/AppProvider.tsx)：读取既有命令协议及错误边界；不修改
- read [../../src/application/service.ts](../../src/application/service.ts)：确认本轮不改服务/存储
- read [../../src/infrastructure/database/executor.ts](../../src/infrastructure/database/executor.ts)：确认数据库执行器不改

实施步骤：

1. 先执行单元与集成验收；这些方法已覆盖的结论不再安排浏览器。主用例中无法由Node证明的真实渲染和事件接线，按原生宿主步骤补齐。
2. 执行两个直接影响回归，不扩大到数据库事务、全部统计算法、历史升级或所有调用链模块。若实际实施改变上述范围，先更新impact及任务/用例。 容器接线检查还覆盖本次重组视图直接触及的tab清理pins、列表/历史加载更多及日历选中回调，核对事件/参数，保留投影及领域规则内部实现。
3. 沿211次逻辑用例访问路线检查每次given并收集实际结果；6个独立补充用例各一次，其内部矩阵保留每行输入与观察，不能把图路线最少视为截图/测试次数最少。
4. 每条证据记录UI版本、页面节点、环境、本次输入及差异；Inter未就绪或宿主无法测量的项记阻碍，不填写通过或相似度百分比。
5. 承接P03-P06局部检查后的整体验收：逐页面容器事件定向回归、真实视图完整路线、全部原有环境及视觉标准保持不变。

Test Case：TC-G-EVIDENCE、TC-G-LAYOUT、TC-G-SCOPE、TC-G-VISUAL、TC-REG-CONTAINERS、TC-REG-CONTROLS、TC-T001～TC-T129（连续ID）

原子需求：R-T001～R-T129（连续ID）

完成标准：

- 本轮要求的每条实际验收均有记录，无未观察即通过；未执行项如实保持未执行。
- 仅在实施范围一致且所有适用断言通过后结束验收；本任务规划当前不执行这些检查。

任务状态：待实施；计划检查：

- node scripts/ui-test.cjs unit；前置任务：P01、P08；未执行
- node scripts/ui-test.cjs integration --case TC-REG-CONTROLS --case TC-REG-CONTAINERS；前置任务：P01、P08；未执行
- node scripts/ui-test.cjs acceptance-route --model plan/task-planning/test-cases.json；前置任务：P01、P08；未执行
