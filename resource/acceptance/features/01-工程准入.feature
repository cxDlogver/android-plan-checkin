# language: en
Feature: 工程准入
  # Product execution NOT_RUN; step definitions not implemented.

  @AC001 @IP01 @FR32 @AT28
  Scenario: AC001 精确依赖与冻结安装可重现
    Given 当前目录尚未创建应用，技术0.8和33项精确候选清单已确认
    When 建立应用清单并执行实际安装、Expo匹配、Android打包和冻结锁重装
    Then 严格依赖检查和Android打包成功，冻结安装未改变锁文件

  @AC002 @IP03 @FR30 @FR32 @AT27 @AT28
  Scenario: AC002 包身份与系统备份排除可重复生成
    Given 正式与开发标识已固定，应用原生目录由配置和插件生成
    When 连续两次生成原生目录并核对最终APK的manifest和备份规则
    Then 包名、最低系统和备份排除保持一致，延期能力不请求权限

  @AC003 @IP03 @FR32 @AT28
  Scenario: AC003 SDK模板原生编译与长期签名
    Given 使用JDK17和SDK57生成工程，长期release证书保存在仓库之外
    When 解析Gradle环境并分别构建development与正式release APK
    Then 两种构建成功，正式APK具备长期证书且不可调试

  @AC004 @IP04 @FR32 @AT24 @AT28
  Scenario: AC004 安卓SQLite连接参数与版本读回
    Given API29或36的原生小样使用SDK57 SQLite且仅有一个业务数据库连接
    When 打开私有库并初始化持久化参数，读回数据库信息
    Then 参数达到wal、FULL、外键开启，实际版本和私有路径被报告

  @AC005 @IP04 @FR14 @FR32 @AT25 @AT28
  Scenario: AC005 原生字体导航和金属小样可独立运行
    Given 两API原生小样内置静态中文400/600/700字体及必要模块
    When 切换Stack与三个Tab，查看渐变和内外阴影，并关闭Metro后启动release
    Then 导航、字体和材质正常展示，独立包没有缺失资源

  @AC006 @IP05 @FR10 @FR32 @AT24 @AT28
  Scenario: AC006 验收工具限定正确设备与隔离数据
    Given 已有Appium服务和API29/36 AVD，验收只使用可丢弃测试设备
    When 建立产品自动化会话并校验设备、应用身份、夹具及正式包测试入口
    Then 会话控制目标应用，测试数据与生产能力隔离

  @AC007 @IP07 @FR10 @FR11 @FR13 @FR29 @FR32 @AT24
  Scenario Outline: AC007 数据库约束拒绝重复或错误引用
    Given 测试原生库已有目标计划和合法记录，外键启用
    When 尝试插入<违规事实>并提交
    Then 事务被拒绝，已有事实保持完整且不存在悬挂引用

    Examples:
      | rowId | 违规事实 |
      | cycle_unique | 同计划同日第二循环记录 |
      | once_unique | 同任务第二终态 |
      | cross_plan_due | 终态引用别计划截止版本 |
      | missing_due | 终态引用不存在截止版本 |
      | actual_mismatch | 完成实际日与businessOn不等 |
      | enum | 未知result或非法weeklyTarget |

  @AC008 @IP07 @FR32 @AT24
  Scenario Outline: AC008 全部待迁移失败时恢复升级前结构与事实
    Given 旧schema含计划、备注、记录和待生效事件，升级需连续执行两步迁移
    When 在第二步迁移<故障点>后重新打开迁移服务
    Then 本次升级没有部分提交，原schema和事实保留，服务返回迁移失败

    Examples:
      | rowId | 故障点 |
      | sql_error | 发生SQL异常 |
      | process_before_commit | 在事务commit之前进程中断 |

  @AC009 @IP07 @FR32 @AT24
  Scenario: AC009 高于代码支持的数据库版本被阻断
    Given 测试库user_version高于当前应用支持版本，已有历史可追溯
    When 调用旧版本支持的迁移初始化服务
    Then 服务返回结构版本不兼容，不执行降级迁移或开放业务写入

  @AC010 @IP08 @FR10 @FR16 @FR32 @AT24
  Scenario: AC010 单连接事务和查询快照不混入其他写入
    Given 测试执行器的简单SQL写事务尚未完成，另有多次读取和写入排队，不调用尚未实现的记录或查询业务服务
    When 并发请求该写事务、同读事务的多条SQL和下一次写入
    Then 读取到一个完整revision的事实，下一次写入按队列顺序执行

  @AC011 @IP30 @FR30 @FR32 @AT27
  Scenario: AC011 日志与构建证据不泄露用户文本和签名材料
    Given 测试名称、说明、备注含唯一敏感标记，正式包经过一次成功和失败保存
    When 审查release日志、自动采集报告和最终交付目录
    Then 日志仅含技术状态，交付目录无私钥或私人数据

  @AC103 @IP07 @FR29 @FR32 @AT23 @AT24
  Scenario: AC103 一次性根删除延迟复合引用级联提交成功
    Given 已归档one_time含due版本、结果、原值、生命周期和相关receipt
    When 通过测试执行器用SQL删除计划根并在同事务写删除凭据，提交后检查外键，不调用尚未实现的永久删除命令
    Then 计划根与全部业务关联一起清除，无级联顺序阻塞

  @AC104 @IP12 @FR10 @FR11 @FR16 @FR23 @AT12 @AT21 @AT24
  Scenario: AC104 revision分配一致且取消版本不复用序号
    Given 计划/记录/字段版本从1开始，存在已取消规则行
    When 修改记录、替代规则和进行一次合法对账
    Then 对象revision单调且每事务每计划只递增一次

  @AC117 @IP02 @FR30 @FR32 @AT27 @AT28
  Scenario: AC117 原生配置生成先于APK编译可独立准入
    Given 应用配置和备份插件已编写，尚未编译APK
    When 连续两次prebuild，检查生成manifest和旧/新备份XML
    Then 生成身份与排除规则一致，可交给IP03编译

  @AC118 @IP17 @FR07 @FR08 @FR14 @FR31 @AT25 @AT26
  Scenario: AC118 金属组件原生展示先于完整页面准入
    Given 原生组件展示页加载静态字体与design-tokens，尚未实现完整今日/日历页面
    When 在API29/36查看MetalSurface、ResultChoice、DateCell和可滚动输入示例
    Then 组件材质、字重、边距与触控基础可用，供完整页面复用

  @AC119 @IP08 @FR10 @FR11 @FR16 @FR23 @AT12 @AT21 @AT24
  Scenario: AC119 revision和CAS原语无业务服务即可验证
    Given 唯一连接内测试对象revision=1，字段规则已有revision1和已取消revision2，尚未实现生产命令
    When 用事务原语执行一次CAS成功、一次旧revision失败、回滚及max加一分配
    Then 成功对象为2，旧revision影响0行，字段下一个版本为3
