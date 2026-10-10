# language: en
Feature: 正式交付
  # Product execution NOT_RUN; step definitions not implemented.

  @AC095 @IP28 @FR01 @FR30 @FR32 @AT01 @AT28
  Scenario: AC095 独立APK关Metro离线首次使用与重启
    Given 正式长期签名非debuggable APK清洁安装，Metro关闭且飞行模式开启
    When 冷启动后手动创建三类计划、保存合法结果备注并关闭重启
    Then 没有开发服务器或网络仍可完成核心闭环和读取原事实

  @AC096 @IP28 @FR32 @AT28
  Scenario: AC096 性能数据和正式包计时满足P95预算
    Given API36 4vCPU/4GiB、393dp/font1，正式包无测试Clock，100计划3年合法夹具已停机载入
    When 准备1次后采集10次冷启、各20次切月和详情原始耗时
    Then 冷启P95≤3000ms且切月/详情P95≤1000ms，数量和分数同时正确

  @AC097 @IP29 @FR16 @FR23 @FR27 @FR32 @AT24 @AT28
  Scenario: AC097 覆盖升级保留历史时区和待生效申请
    Given 旧schema验证包用正式同包同签名，包含记录、原值、固定zone和未来规则/状态事件
    When 安装递增versionCode新APK覆盖并启动，不卸载或清数据
    Then 迁移成功且全部合法事实保留，未来事件按原生效日发生

  @AC098 @IP29 @FR30 @FR32 @AT27 @AT28
  Scenario: AC098 备份禁用和换机边界分别验证
    Given 最终APK静态规则正确且API29/36测试数据已知
    When 执行适用于设备的系统备份/恢复或迁移验证并核对实际私有目录
    Then 应用业务数据不参与已验证路径，其他厂商未测不被声称通过

  @AC099 @IP26 @FR01 @FR02 @FR03 @FR04 @FR05 @FR06 @FR07 @FR08 @FR09 @FR10 @FR11 @FR12 @FR13 @FR14 @FR15 @FR16 @FR17 @FR18 @FR19 @FR20 @FR21 @FR22 @FR23 @FR24 @FR25 @FR26 @FR27 @FR28 @FR29 @FR30 @FR31 @FR32 @AT01 @AT02 @AT03 @AT04 @AT05 @AT06 @AT07 @AT08 @AT09 @AT10 @AT11 @AT12 @AT13 @AT14 @AT15 @AT16 @AT17 @AT18 @AT19 @AT20 @AT21 @AT22 @AT23 @AT24 @AT25 @AT26 @AT27 @AT28
  Scenario: AC099 FR与AT和每个参数执行结果闭合
    Given IP26阶段的领域/SQL/UI实例已汇集，矩阵和正式交付专项尚在后续任务
    When 检查32FR、28AT映射及本阶段每个参数/双API功能结果
    Then 本阶段功能分项完整，无漏映射或用设计/环境PASS代替产品结果

  @AC100 @IP30 @FR30 @FR32 @AT27 @AT28
  Scenario: AC100 交付清单证据一致且签名资料不外泄
    Given 所有首版必需门槛已有执行结论，交付目录候选已组装
    When 核对APK、构建清单、验收报告、性能升级数据和安装说明
    Then 交付身份摘要一致，可独立安装覆盖升级且限制说明准确
