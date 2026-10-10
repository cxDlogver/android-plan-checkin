# 计划打卡 Android V1

免登录、本机保存的安卓个人计划与执行记录工具，技术方向React Native/Expo。三类计划、记录/补记、暂停恢复/归档、月历、历史统计与本机设置已实现；代码与验收结果分别跟踪。最终目标是Windows安卓模拟器实测与无需开发服务器的独立APK。

## 运行与证据

[公开仓库](https://github.com/cxDlogver/android-plan-checkin) · [实时开发进度](resource/progress/开发进度.md) · [代码与验证交付记录](resource/progress/代码交付记录.md) · [构建与签名](resource/progress/构建与签名.md)

使用 Node 24.21.0、pnpm 10.28.2 和 JDK 17；Android SDK 编译/目标36，最低29。项目依赖33项精确固定，TypeScript根据Expo实际检查调整为6.0.3，原因与原始失败记录见[技术执行调整](resource/progress/技术执行调整.md)。

```powershell
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:domain
$env:APP_VARIANT = 'development'
pnpm exec expo prebuild --platform android --no-install
pnpm exec expo run:android
```

工程分为纯领域规则、单SQLite执行器/应用服务、查询投影、界面与文件路由。开发包 `/native` 提供原生模块核查页；正式bundle通过Metro别名替换为空入口，不包含开发核查实现。全部事实保存在应用私有数据库，字体400/600/700随包离线加载。

本机证据命令：`node scripts/p1.cjs <检查名>`；其工具路径可由 `ANDROID_AI_TOOL_ROOT` 覆盖。检查名包括 `typecheck`、`bundle`、`domain-compile`、`domain-tests`、`query-tests`、`integration-compile`、`integration-tests`、`signing-check`、`prebuild-first`、`prebuild-repeat`。已通过且输入/输出/证据摘要未变时自动SKIP；输入变化仅执行受影响项。SQLite宿主集成测试使用Node原生SQLite和测试专用Expo适配层，不能替代Android桥接验收。

签名密钥在仓库外保存。未提供签名环境或原生身份错误时，正式release构建拒绝执行；不得把模板debug签名当正式产物。`.cache`、`.artifacts`、生成的 `android/`、密钥和本地环境文件均不入Git。

- [详细需求：截图紧邻功能正文、32项功能与28组验收](resource/设计需求文档-计划打卡-Android-v1.md)
- [技术设计文档（0.8已确认基线）](resource/技术设计文档-计划打卡-Android-v1.md)
- [实施计划 checklist（1.0评审稿，30个实施项）](resource/实施计划-checklist-计划打卡-Android-v1.md)
- [BDD验收 checklist（1.0评审稿，场景/操作/结果、断言与证据）](resource/BDD验收-checklist-计划打卡-Android-v1.md)
- [实施与BDD图文浏览：搜索、主题导航、按需展开](resource/acceptance/浏览.html)
- [IP–AC–FR–AT追踪目录](resource/acceptance/追踪目录.json)、[Gherkin场景文件](resource/acceptance/features/)、[单实例报告空模板](resource/acceptance/单实例报告模板.json)
- [技术详细规格：数据/迁移](resource/technical/数据结构与迁移契约.md)、[命令/查询](resource/technical/命令与查询契约.md)、[日期/统计](resource/technical/日期生命周期与统计决策表.md)、[验收/构建](resource/technical/验收与构建证据规范.md)
- [依赖可行性核查：精确版本、严格锁解析与运行门槛](resource/依赖可行性核查-20261009.md)
- [技术决策与确认记录](resource/技术决策与待确认项.md)
- [需求分析与待确认项](resource/需求分析与待确认项.md)
- [23页图文对照预览：截图、详细需求与验收](resource/design/preview.html)
- [UI/UX规格](resource/UIUX-计划打卡-Android-v1.md)
- [可编辑Pen画布](resource/ui.pen)
- [设计检查记录](resource/design/设计检查记录.md)
- [Windows模拟器验证方案](resource/Windows安卓模拟器验证方案.md)
- [本机模拟器与AI自动化验收就绪评估](resource/模拟器与AI自动化验收就绪评估-20261009.md)
- [安卓AI验收环境配置：版本、启动脚本、实测截图](resource/安卓AI验收环境配置记录-20261009.md)
- [设计令牌](resource/design/design-tokens.json)
- [页面清单](resource/design/page-map.json)

首版为个人核心闭环：三类计划、今日结果确认、文字备注、合法补记、日历与全部历史统计。普通记录只能当天改；补记保存后立即只读；不允许撤回。暂停/归档禁止补记，恢复后也不能补暂停前日期。

本轮已明确新建固定星期默认不选，必须手动选择至少一天；“每日”为显式全选快捷操作。实施和BDD文档按固定IP/AC编号双向关联，每个参数/设备实例单独保存断言及证据。当前实现及命令结果见实时进度；完整产品BDD与八组合仍待原生执行。.feature是验收规格，尚无全量自动化步骤定义。

运行中/暂停计划删除后立即移入归档，保留历史；归档后无恢复，只有查看和永久删除。循环到期次日自动归档；一次性普通终态次日、历史补报立即归档。暂停不可编辑，只改状态；固定时区在首次使用确定并全部计划共用。

账号、云同步、社交、分组、提醒、照片、数值、备份均延期。

设计以银色金属渐变、阴影、低圆角、粗体标题与绿/红/橙结果为主。日历今天浅色填充、无点/完成进度；其他日期全完成仅✓，否则完成数/总数，零项留空。周目标仅当天已有记录计总数，一次性安排跟随截止、终态只计结果业务日。

日历分数10sp金黄色，小于12sp日期。月历下含义介绍已移除；日期/计划数量标题下面用状态筛选框，全部/已完成/未完成只筛选明细，不改变汇总或历史统计。

23页PNG已导出，节点布局无裁切，截图与对应需求并排浏览。新增跨日重新确认状态：首次记录页跨午夜阻止旧提交、保留输入，合法时显式进入补记确认；整周暂停在周结束时中断连续且不进达标率分母。需求与设计1.1已通过Q33整体确认；1.0/Q27历史保留，可编辑Pen最新保存状态见设计检查记录。

技术基线0.8已通过T15整体确认，包含9表DDL、11个命令/查询契约、日期/生命周期/统计决策表及验收/构建证据规范。T1–T14逐项明确，名称计划打卡，正式包com.xiang.plancheckin，开发包com.xiang.plancheckin.dev；P0技术设计完成。宿主SQL原型13项检查PASS，不能替代Android原生验证。

SDK57精确依赖、Node要求和静态中文字体已核查；33个应用/开发依赖＋pnpm通过发布元数据核查，完整依赖图strict peer解析及冻结锁文件复核PASS。SQLite候选内置3.50.3，方案严格保持单原生连接以避开已知WAL-reset多连接触发前提；实际原生版本与Gradle9.3.1/AGP8.12构建仍需P1留证。

独立Node24、现有JDK17、SDK/ADB、API29/36 AVD与Appium3.8.0/UiAutomator2 8.7.0已按授权配置；WHPX、两套模拟器启动及原生点击/输入/返回/截图均PASS，一键启停及API36控制复核PASS。F盘空闲约36.6GiB，原空间阻碍解除。应用依赖安装、冻结锁复核、类型检查和Android JS打包已执行；原生构建结果持续写入，完整产品验收与独立release仍单列跟踪。
