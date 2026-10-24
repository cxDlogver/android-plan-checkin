# 代码开发 Plan

基于现有需求图一一建立主测试图，并复用需求审查HTML新增测试视图；保留已有代码开发计划。

本阶段不实现应用代码、不执行产品验收。实现期间仅必要静态检查和单元测试；所有实现项完成后再进入完整验收。

## 现状与风险

- `package.json`：已有 typecheck/test:domain；旧结果不作为本轮通过。
- `src/domain/model.ts`：三种计划、命令及数据库事实模型已存在。
- `src/domain/commands.ts`：已有字段校验、命令和回执；UI 补齐不要求重写规则。
- `src/domain/date.ts`：固定时区、业务日期、周起点和42格月份投影。
- `src/application/service.ts`：事务与回执共用；保存反馈需保留真实提交与读取顺序。
- `src/application/projections.ts`：游标依赖日期/时区/revision；缓存按身份和事实引用失效。
- `src/state/AppProvider.tsx`：请求序号防旧快照覆盖；持久读错误阻断；跨日/前台刷新已有。
- `src/ui/metal.tsx`：共享组件影响全部页面及48dp、大字号、键盘与Back。
- `src/features/calendar.tsx`：切月保留选中日和明细；选日重置筛选，符合人工确认。
- `src/features/plan-form.tsx`：类型切换提示已有；保存禁用只判断busy与固定星期为空，其余必填主要提交后校验。
- `src/features/record-form.tsx`：确认、修订、补记、跨日已有；成功直接返回，未见统一已保存到本机反馈。
- `src/features/draft.ts`：dirty/busy、弹窗防重入和确认后放行。
- `src/features/today.tsx`：四分区与返回pin已有；真空态和今日无执行项共用Empty，需核对文案。
- `src/features/plans.tsx`：筛选、分页和revision重置已有，需防漏项重复。
- `src/features/plan-detail.tsx`：历史分页、统计、规则和两次删除确认已有。
- `src/features/settings.tsx`：本机版本/时区与数据说明已有；延期功能属于范围约束。
- `src/features/shared.tsx`：PlanCard与结果文案/颜色跨页面复用。
- `tests/domain/projections.test.ts`：稳定分页、缓存失效、42格及历史分页单测可复用。
- `tests/domain/bdd-validation.test.ts`：Unicode、换行、mask、周目标边界已有。
- `tests/domain/bdd-service-rules.test.ts`：周规则替换、统计、一次性冻结截止测试已有。
- `tests/integration/database.test.ts`：SQLite事务回滚/回执/升级测试放最终验收，不冒充开发单测。
- `src/infrastructure/database/executor.ts`：单连接队列、事务和外键检查；本轮UI计划不改schema。
- `scripts/p1.cjs`：旧流程会写历史progress；本轮仅调查，不调用旧证据归档。

## 实现顺序

### 共享视觉与交互组件

任务 `shared`；依赖：无

位置：`src/ui/metal.tsx`, `src/features/shared.tsx`

实施：按设计令牌核对字号、渐变、低圆角、边距与状态符号；组件保持48dp命中和字号缩放；复用现有 Metal/Button/Field/DateField，不改变组件消费者的事件和数据契约

完成条件：公共组件覆盖23画板使用的视觉样式；新增差异有明确UI来源；不移除可访问名称、禁用状态、日期边界与原导航事件

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。

### 启动、今日与导航

任务 `boot`；依赖：shared

位置：`src/state/AppProvider.tsx`, `src/features/today.tsx`, `src/features/settings.tsx`, `app/(tabs)/_layout.tsx`

实施：区分真实零计划和今日无可执行项，按PRD还原入口与文案；保持读取中/错误阻断、请求序号防乱序、来源返回和今日pin

完成条件：启动/读取失败/今日空态具有不同呈现；不预置样例计划；设置延期能力仅作为范围限制，无新增不可用入口

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。

### 创建与编辑表单

任务 `create`；依赖：shared

位置：`src/features/plan-form.tsx`, `src/domain/commands.ts`

实施：提取或复用同一合法性规则，在输入变化后计算保存资格；避免按钮规则与提交校验分叉；保留切类型确认、公共字段、Unicode长度、规则待生效初值；业务规则已有则不重写

完成条件：空名称、非法N、非法日期、未选星期均不能最终保存；待生效字段与未改变字段不会相互覆盖，错误贴近字段且可朗读

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。
- unit：`pnpm test:domain` — 复用现有纯规则/投影边界单测，保护本任务受影响行为。

### 记录确认与保存反馈

任务 `record`；依赖：shared, create

位置：`src/features/record-form.tsx`, `src/state/AppProvider.tsx`, `src/features/today.tsx`, `src/features/calendar.tsx`

实施：在真实事务成功与来源页刷新后提供已保存到本机反馈；失败不显示成功；保留冻结信封重试、当日修改、补记立即只读、跨日重新确认与保存中禁用

完成条件：成功反馈可在原来源页看到；取消不落盘；失败保留输入，重复提交不重复创建，跨日不静默转补记

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。

### 日历、筛选与回看

任务 `calendar`；依赖：shared, record

位置：`src/features/calendar.tsx`, `src/application/projections.ts`, `src/ui/metal.tsx`

实施：保留已确认切月只浏览月份，不改变原选中日与明细；按UI核对今天/选中独立、未来只读、金色分数、七列对齐；优先复用现有月投影

完成条件：全量集合计算日历分母，筛选仅改明细；切日重置，记录返回保留；大字号不得截断分数或降低48dp命中；不得引入缓存过期或重复分页

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。
- unit：`pnpm test:domain` — 复用现有纯规则/投影边界单测，保护本任务受影响行为。

### 详情、列表与生命周期

任务 `manage`；依赖：shared, create, record

位置：`src/features/plans.tsx`, `src/features/plan-detail.tsx`, `src/application/projections.ts`

实施：复用已有运行/暂停/归档、待生效取消和两阶段删除；按需求逐项核对呈现；不通过视觉调整改变归档优先级、历史只读或分页身份

完成条件：取消/删除确认和失败反馈有来源明确文案；历史数据不被视觉任务改写；游标分页不漏项不重复；永久删除后不能显示旧详情

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。
- unit：`pnpm test:domain` — 复用现有纯规则/投影边界单测，保护本任务受影响行为。

### 统计、日期和规则边界

任务 `stats`；依赖：calendar, manage

位置：`src/domain/rules.ts`, `src/domain/date.ts`, `src/application/projections.ts`, `src/features/plan-detail.tsx`

实施：先逐条对照已有单测与需求；仅对已证实差异补代码；保留固定率排除跳过、日历含跳过、部分周和整周暂停、冻结截止及固定时区

完成条件：同一数据的分子分母按各自口径可复核；代码差异有对应边界单测，未经证实不重构领域规则

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。
- unit：`pnpm test:domain` — 复用现有纯规则/投影边界单测，保护本任务受影响行为。

### 草稿、返回与弹层

任务 `draft`；依赖：create, record

位置：`src/features/draft.ts`, `src/ui/metal.tsx`, `src/features/plan-form.tsx`, `src/features/record-form.tsx`

实施：复用现有useDraftGuard，核对继续编辑/放弃、保存忙碌和弹层关闭的优先级；不得在返回时写入草稿或改变来源页上下文

完成条件：重复Back不叠对话框，继续编辑保留输入，放弃仅清草稿；保存中不放行离开，不把日期弹层关闭当成页面返回

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。

### 最终验收夹具与证据接口

任务 `prepare`；依赖：boot, calendar, manage, stats, draft

位置：`src/verification/fixtures.ts`, `src/verification/runtime-contract.ts`, `tests/domain/projections.test.ts`, `tests/domain/AppProvider-refresh.test.ts (planned)`

实施：把每段测试准备具体化：计划/规则/记录、业务时区/时间、故障注入位置、清理与恢复；不能修改业务规则以凑可达；映射设备矩阵、证据定位与断言实例；本轮暂不新增回归测试项。；只准备验收驱动和文档；开发结束前不启动浏览器/模拟器完成产品验收

完成条件：每个测试实例可由明确数据与操作复现；待决不自动填默认；准备接口与生产代码隔离；最终验收前所有实现项和开发检查完成

必要开发检查：
- static：`pnpm typecheck` — 核对组件属性、状态与领域类型；本轮尚未运行。
- unit：`pnpm test:domain` — 复用现有纯规则/投影边界单测，保护本任务受影响行为。

## 最终验收与待决

按 test-plan.json 的测试项及实例验收；继承路线先解决条件冲突与准备缺口，再执行产品功能/视觉验收。每项保留断言实测及证据定位。

设备矩阵：API29/360dp/100%；API29/360dp/200%；API29/393dp/100%；API29/393dp/200%；API36/360dp/100%；API36/360dp/200%；API36/393dp/100%；API36/393dp/200%

标准功能完整覆盖；页面/组件和有差异状态的视觉与可访问性覆盖全矩阵，具体映射待准备。

- 上游需求分析尚未正式验收：可作为规划草案，不能直接成为正式开发基线。
- 逐段数据、时钟、故障与恢复操作待具体化：有限域路线不是已经准备好的可执行夹具；系统事件不能冒充可点击按钮。
- 设备矩阵与共享视觉需要映射到验收实例：标准情景不能代表API29/36、360/393dp与100/200%全部组合。
- 审查 HTML 尚无真实浏览器观察证据：只验证嵌入数据与模拟Canvas，不声称目测通过。