# 计划打卡 Android V1｜BDD验收 checklist

> 版本1.0评审稿；依据已确认PRD/UI 1.1和技术0.8。所有产品验收NOT_RUN。

**120个场景 · 281个场景/参数实例 · 32项需求 · 28组原验收。** 设备配置另外展开，不把文档检查当产品通过。

## 从这里阅读

- [图文浏览页](acceptance/浏览.html)：搜索任务/场景/需求编号，查看操作、结果、断言和对应设计参考；按需展开参数与证据。
- [实施计划](实施计划-checklist-计划打卡-Android-v1.md)：按P1–P4执行，每项列前置、工作、产物及本阶段退出范围。
- [执行与证据规则](acceptance/执行与证据规则.md)：Given/When/Then、设备矩阵、勾选规则、证据格式及边界。
- [FR/AT追踪索引](acceptance/FR-AT追踪索引.md)：原需求 → 具体场景 → 实施任务。

先读与当前任务相关的分册，再看具体AC。业务步骤直接展示；规范Gherkin、参数和证据详情可展开。以下checkbox均未执行；.feature只有规格，尚无step definitions。

## 主题分册

| 主题 | 场景数 | 参数实例数 | 详细 checklist |
| --- | ---: | ---: | --- |
| 工程准入 | 16 | 22 | [打开分册](acceptance/scenarios/01-工程准入.md) |
| 日期与时区 | 4 | 9 | [打开分册](acceptance/scenarios/02-日期与时区.md) |
| 创建与编辑 | 11 | 38 | [打开分册](acceptance/scenarios/03-创建与编辑.md) |
| 确认与记录 | 23 | 58 | [打开分册](acceptance/scenarios/04-确认与记录.md) |
| 生命周期 | 12 | 18 | [打开分册](acceptance/scenarios/05-生命周期.md) |
| 规则版本 | 5 | 9 | [打开分册](acceptance/scenarios/06-规则版本.md) |
| 统计回顾 | 9 | 28 | [打开分册](acceptance/scenarios/07-统计回顾.md) |
| 日历与筛选 | 11 | 19 | [打开分册](acceptance/scenarios/08-日历与筛选.md) |
| 页面与异常 | 9 | 15 | [打开分册](acceptance/scenarios/09-页面与异常.md) |
| 矩阵与视觉 | 5 | 13 | [打开分册](acceptance/scenarios/10-矩阵与视觉.md) |
| 正式交付 | 6 | 6 | [打开分册](acceptance/scenarios/11-正式交付.md) |
| 数据与规则准入 | 9 | 46 | [打开分册](acceptance/scenarios/12-数据与规则准入.md) |

## 验收总 checklist

### 工程准入

- [x] [AC001｜精确依赖与冻结安装可重现](acceptance/scenarios/01-工程准入.md#ac001)
- [x] [AC002｜包身份与系统备份排除可重复生成](acceptance/scenarios/01-工程准入.md#ac002)
- [x] [AC003｜SDK模板原生编译与长期签名](acceptance/scenarios/01-工程准入.md#ac003)
- [ ] [AC004｜安卓SQLite连接参数与版本读回](acceptance/scenarios/01-工程准入.md#ac004)
- [ ] [AC005｜原生字体导航和金属小样可独立运行](acceptance/scenarios/01-工程准入.md#ac005)
- [ ] [AC006｜验收工具限定正确设备与隔离数据](acceptance/scenarios/01-工程准入.md#ac006)
- [ ] [AC007｜数据库约束拒绝重复或错误引用](acceptance/scenarios/01-工程准入.md#ac007)
- [ ] [AC008｜全部待迁移失败时恢复升级前结构与事实](acceptance/scenarios/01-工程准入.md#ac008)
- [ ] [AC009｜高于代码支持的数据库版本被阻断](acceptance/scenarios/01-工程准入.md#ac009)
- [ ] [AC010｜单连接事务和查询快照不混入其他写入](acceptance/scenarios/01-工程准入.md#ac010)
- [ ] [AC011｜日志与构建证据不泄露用户文本和签名材料](acceptance/scenarios/01-工程准入.md#ac011)
- [ ] [AC103｜一次性根删除延迟复合引用级联提交成功](acceptance/scenarios/01-工程准入.md#ac103)
- [ ] [AC104｜revision分配一致且取消版本不复用序号](acceptance/scenarios/01-工程准入.md#ac104)
- [x] [AC117｜原生配置生成先于APK编译可独立准入](acceptance/scenarios/01-工程准入.md#ac117)
- [ ] [AC118｜金属组件原生展示先于完整页面准入](acceptance/scenarios/01-工程准入.md#ac118)
- [ ] [AC119｜revision和CAS原语无业务服务即可验证](acceptance/scenarios/01-工程准入.md#ac119)

### 日期与时区

- [ ] [AC012｜首次时区获取失败不猜测日期](acceptance/scenarios/02-日期与时区.md#ac012)
- [ ] [AC013｜换设备时区不移动计划今天与历史](acceptance/scenarios/02-日期与时区.md#ac013)
- [ ] [AC014｜公历加一天覆盖DST和月年边界](acceptance/scenarios/02-日期与时区.md#ac014)
- [ ] [AC015｜前台午夜重算不强制跳选中日期](acceptance/scenarios/02-日期与时区.md#ac015)

### 创建与编辑

- [ ] [AC016｜新建默认值和星期未选状态](acceptance/scenarios/03-创建与编辑.md#ac016)
- [ ] [AC017｜文本码点边界与单行名称](acceptance/scenarios/03-创建与编辑.md#ac017)
- [ ] [AC018｜切换类型保留共通字段并拒绝隐藏字段混入](acceptance/scenarios/03-创建与编辑.md#ac018)
- [ ] [AC019｜循环日期不得过去或倒置](acceptance/scenarios/03-创建与编辑.md#ac019)
- [ ] [AC020｜固定星期选择与每日摘要一致](acceptance/scenarios/03-创建与编辑.md#ac020)
- [ ] [AC021｜每周目标只接受1至7整数](acceptance/scenarios/03-创建与编辑.md#ac021)
- [ ] [AC022｜同名计划保持独立且创建成功导航详情](acceptance/scenarios/03-创建与编辑.md#ac022)
- [ ] [AC023｜暂停归档和不可变字段拒绝编辑](acceptance/scenarios/03-创建与编辑.md#ac023)
- [ ] [AC101｜一次性创建截止必填且没有循环字段](acceptance/scenarios/03-创建与编辑.md#ac101)
- [ ] [AC107｜新建表单跨日重新校验且不自动挪日期](acceptance/scenarios/03-创建与编辑.md#ac107)
- [ ] [AC120｜三类合法新建在八组合最终保存](acceptance/scenarios/03-创建与编辑.md#ac120)

### 确认与记录

- [ ] [AC024｜点击结果仅预选，取消不生成记录](acceptance/scenarios/04-确认与记录.md#ac024)
- [ ] [AC025｜最终确认普通记录后本机持久保存](acceptance/scenarios/04-确认与记录.md#ac025)
- [ ] [AC026｜不要做计划明确行为未发生与发生](acceptance/scenarios/04-确认与记录.md#ac026)
- [ ] [AC027｜普通当日修正加载当前值并保留首次原值](acceptance/scenarios/04-确认与记录.md#ac027)
- [ ] [AC028｜无变化保存不制造修正或新revision](acceptance/scenarios/04-确认与记录.md#ac028)
- [ ] [AC029｜历史与補记保存后的结果备注均只读](acceptance/scenarios/04-确认与记录.md#ac029)
- [ ] [AC030｜固定历史资格按目标星期判断](acceptance/scenarios/04-确认与记录.md#ac030)
- [ ] [AC031｜补记只限当前运行阶段合法空日](acceptance/scenarios/04-确认与记录.md#ac031)
- [ ] [AC032｜首次记录跨午夜拒绝旧保存再显式补记](acceptance/scenarios/04-确认与记录.md#ac032)
- [ ] [AC033｜跨日后状态不合法不提供补记确认](acceptance/scenarios/04-确认与记录.md#ac033)
- [ ] [AC034｜已有记录修改跨午夜直接只读](acceptance/scenarios/04-确认与记录.md#ac034)
- [ ] [AC035｜一次性完成按实际日期区分按时与迟完成](acceptance/scenarios/04-确认与记录.md#ac035)
- [ ] [AC036｜一次性完成日期范围和必填校验](acceptance/scenarios/04-确认与记录.md#ac036)
- [ ] [AC037｜一次性失败取消独立于循环跳过](acceptance/scenarios/04-确认与记录.md#ac037)
- [ ] [AC038｜一次性三结果同日可改但业务日期截止固定](acceptance/scenarios/04-确认与记录.md#ac038)
- [ ] [AC039｜一次性首次跨日不自动补报失败取消](acceptance/scenarios/04-确认与记录.md#ac039)
- [ ] [AC040｜重复同命令及跨日成功重试只返回一次事实](acceptance/scenarios/04-确认与记录.md#ac040)
- [ ] [AC041｜不同命令争抢同日或旧revision不静默覆盖](acceptance/scenarios/04-确认与记录.md#ac041)
- [ ] [AC042｜命令ID复用、过期和删除重放被拒绝](acceptance/scenarios/04-确认与记录.md#ac042)
- [ ] [AC043｜写失败或空间不足保留输入并完整回滚](acceptance/scenarios/04-确认与记录.md#ac043)
- [ ] [AC044｜commit前后进程中断恢复事实而非草稿](acceptance/scenarios/04-确认与记录.md#ac044)
- [ ] [AC102｜重试窗口边界与凭据限批清理](acceptance/scenarios/04-确认与记录.md#ac102)
- [ ] [AC105｜未选结果不能最终保存且提交中禁重复操作](acceptance/scenarios/04-确认与记录.md#ac105)

### 生命周期

- [ ] [AC045｜暂停明天生效且今天仍可记录](acceptance/scenarios/05-生命周期.md#ac045)
- [ ] [AC046｜恢复明天开启新阶段但不补旧日期](acceptance/scenarios/05-生命周期.md#ac046)
- [ ] [AC047｜生效前取消申请不改变执行阶段](acceptance/scenarios/05-生命周期.md#ac047)
- [ ] [AC048｜跨日已生效申请不可取消且旧日期确认不能漂移](acceptance/scenarios/05-生命周期.md#ac048)
- [ ] [AC049｜运行暂停删除均立即归档而保留全部历史](acceptance/scenarios/05-生命周期.md#ac049)
- [ ] [AC050｜手动归档当天保留记录并取消空要求](acceptance/scenarios/05-生命周期.md#ac050)
- [ ] [AC051｜自然结束包含末日并在次日归档](acceptance/scenarios/05-生命周期.md#ac051)
- [ ] [AC052｜一次性普通终态与历史补报归档边界不同](acceptance/scenarios/05-生命周期.md#ac052)
- [ ] [AC053｜长时间离线对账使用原边界且归档优先](acceptance/scenarios/05-生命周期.md#ac053)
- [ ] [AC054｜拒绝旧提交不回滚独立合法对账](acceptance/scenarios/05-生命周期.md#ac054)
- [ ] [AC055｜开始前管理不产生负执行区间](acceptance/scenarios/05-生命周期.md#ac055)
- [ ] [AC056｜归档后永久删除取消保留确认才清空](acceptance/scenarios/05-生命周期.md#ac056)

### 规则版本

- [ ] [AC057｜固定星期明天生效且不改旧资格](acceptance/scenarios/06-规则版本.md#ac057)
- [ ] [AC058｜周目标严格下周一生效并以最后值为准](acceptance/scenarios/06-规则版本.md#ac058)
- [ ] [AC059｜pending优先显示且回current取消该字段](acceptance/scenarios/06-规则版本.md#ac059)
- [ ] [AC060｜结束截止即时保存及逾期延期](acceptance/scenarios/06-规则版本.md#ac060)
- [ ] [AC061｜规则生效日期确认跨边界需重新确认](acceptance/scenarios/06-规则版本.md#ac061)

### 统计回顾

- [ ] [AC062｜固定今天提交立即计入，跳过排除率分母](acceptance/scenarios/07-统计回顾.md#ac062)
- [ ] [AC063｜过去未知、补记和零分母有明确公式](acceptance/scenarios/07-统计回顾.md#ac063)
- [ ] [AC064｜显示统计起止与分母集合分别处理](acceptance/scenarios/07-统计回顾.md#ac064)
- [ ] [AC065｜固定连续按应执行次数并按事件中断](acceptance/scenarios/07-统计回顾.md#ac065)
- [ ] [AC066｜周目标超过目标仍显示实际天数且日唯一](acceptance/scenarios/07-统计回顾.md#ac066)
- [ ] [AC067｜历史周率只纳入已结束完整周](acceptance/scenarios/07-统计回顾.md#ac067)
- [ ] [AC068｜部分周排除率分母且周结束才中断](acceptance/scenarios/07-统计回顾.md#ac068)
- [ ] [AC069｜整周暂停不计率但结束时打断连续](acceptance/scenarios/07-统计回顾.md#ac069)
- [ ] [AC070｜周日自然结束与即时归档完整周不同](acceptance/scenarios/07-统计回顾.md#ac070)

### 日历与筛选

- [ ] [AC071｜非今日每格仅一个汇总下标](acceptance/scenarios/08-日历与筛选.md#ac071)
- [ ] [AC072｜今天浅色填充与选中边框独立](acceptance/scenarios/08-日历与筛选.md#ac072)
- [ ] [AC073｜日历分母与固定历史分母不能混用](acceptance/scenarios/08-日历与筛选.md#ac073)
- [ ] [AC074｜周目标只把已有记录加入每日集合](acceptance/scenarios/08-日历与筛选.md#ac074)
- [ ] [AC075｜一次性终态替代截止安排且按业务日归属](acceptance/scenarios/08-日历与筛选.md#ac075)
- [ ] [AC076｜手动归档一次性只保留过去截止项](acceptance/scenarios/08-日历与筛选.md#ac076)
- [ ] [AC077｜未来固定截止安排只读0/T](acceptance/scenarios/08-日历与筛选.md#ac077)
- [ ] [AC078｜筛选只改变明细不改变全局总数](acceptance/scenarios/08-日历与筛选.md#ac078)
- [ ] [AC079｜切日重置筛选，记录返回恢复并重算数量](acceptance/scenarios/08-日历与筛选.md#ac079)
- [ ] [AC080｜筛选关闭空结果与独立周补记区准确](acceptance/scenarios/08-日历与筛选.md#ac080)
- [ ] [AC081｜月份跨格和回今天使用真实完整日期](acceptance/scenarios/08-日历与筛选.md#ac081)

### 页面与异常

- [ ] [AC082｜初始化加载和读库错误不伪装空态](acceptance/scenarios/09-页面与异常.md#ac082)
- [ ] [AC083｜今日四分区包含全部未终结一次性](acceptance/scenarios/09-页面与异常.md#ac083)
- [ ] [AC084｜保存成功就地反馈下次刷新才归已记录](acceptance/scenarios/09-页面与异常.md#ac084)
- [ ] [AC085｜计划列表筛选状态与稳定排序可找到全部历史](acceptance/scenarios/09-页面与异常.md#ac085)
- [ ] [AC086｜历史按当时规则倒序分页不漏项](acceptance/scenarios/09-页面与异常.md#ac086)
- [ ] [AC087｜目标删除或读失败不能从旧缓存继续写](acceptance/scenarios/09-页面与异常.md#ac087)
- [ ] [AC088｜草稿退出与Back优先级](acceptance/scenarios/09-页面与异常.md#ac088)
- [ ] [AC089｜本机设置显示真实版本和无备份边界](acceptance/scenarios/09-页面与异常.md#ac089)
- [ ] [AC106｜一次性回顾显示实际日期而非固定完成率](acceptance/scenarios/09-页面与异常.md#ac106)

### 矩阵与视觉

- [ ] [AC090｜金属材质字体边距与结果语义](acceptance/scenarios/10-矩阵与视觉.md#ac090)
- [ ] [AC091｜8组合读回与核心操作逐配置验收](acceptance/scenarios/10-矩阵与视觉.md#ac091)
- [ ] [AC092｜六行日历和大数字号不截断](acceptance/scenarios/10-矩阵与视觉.md#ac092)
- [ ] [AC093｜键盘系统栏与两种导航Back可用](acceptance/scenarios/10-矩阵与视觉.md#ac093)
- [ ] [AC094｜TalkBack朗读完整日期结果权限及筛选数量](acceptance/scenarios/10-矩阵与视觉.md#ac094)

### 正式交付

- [ ] [AC095｜独立APK关Metro离线首次使用与重启](acceptance/scenarios/11-正式交付.md#ac095)
- [ ] [AC096｜性能数据和正式包计时满足P95预算](acceptance/scenarios/11-正式交付.md#ac096)
- [ ] [AC097｜覆盖升级保留历史时区和待生效申请](acceptance/scenarios/11-正式交付.md#ac097)
- [ ] [AC098｜备份禁用和换机边界分别验证](acceptance/scenarios/11-正式交付.md#ac098)
- [ ] [AC099｜FR与AT和每个参数执行结果闭合](acceptance/scenarios/11-正式交付.md#ac099)
- [ ] [AC100｜交付清单证据一致且签名资料不外泄](acceptance/scenarios/11-正式交付.md#ac100)

### 数据与规则准入

- [ ] [AC108｜日期适配和初始化服务独立于页面验证](acceptance/scenarios/12-数据与规则准入.md#ac108)
- [ ] [AC109｜创建编辑和待生效规则服务的精确出口](acceptance/scenarios/12-数据与规则准入.md#ac109)
- [ ] [AC110｜生命周期对账可在无页面时验证](acceptance/scenarios/12-数据与规则准入.md#ac110)
- [ ] [AC111｜记录权限和原值服务不依赖确认页](acceptance/scenarios/12-数据与规则准入.md#ac111)
- [ ] [AC112｜命令事务、跨日和重放服务出口](acceptance/scenarios/12-数据与规则准入.md#ac112)
- [ ] [AC113｜固定聚合和连续的数值出口](acceptance/scenarios/12-数据与规则准入.md#ac113)
- [ ] [AC114｜周聚合按完整自然周和真实终止边界计算](acceptance/scenarios/12-数据与规则准入.md#ac114)
- [ ] [AC115｜一次性终态与冻结截止的服务出口](acceptance/scenarios/12-数据与规则准入.md#ac115)
- [ ] [AC116｜查询DTO的日集合、排序与分页出口](acceptance/scenarios/12-数据与规则准入.md#ac116)

## 阶段门槛

- [ ] G2：真实依赖安装、配置、原生构建和双API小样通过（IP01–IP05）。
- [ ] G3：日期、规则、命令、统计、双API SQLite独立数据验收通过（IP06–IP16）。
- [ ] G4：页面功能、全参数及八组合、视觉/键盘/Back/TalkBack通过（IP17–IP27）。
- [ ] G5：正式包离线、性能、升级、隐私与完整交付证据通过（IP28–IP30）。

任务可按本阶段退出范围完成；AC父项等全部规定参数/配置齐全才勾。任何必需项FAIL、NOT_RUN或BLOCKED都不能标其门槛通过。

## 评审与产物

- [ ] REVIEW：用户确认实施/BDD1.0共同理解，转为执行基线。
- [ ] EXECUTION：全部必需实例的断言、证据和回归完整后，关闭产品验收。

[追踪目录](acceptance/追踪目录.json) · [Gherkin场景](acceptance/features/) · [报告空模板](acceptance/单实例报告模板.json) · [文档检查报告](review/实施与BDD文档检查结果.json)

