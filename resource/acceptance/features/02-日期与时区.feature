# language: en
Feature: 日期与时区
  # Product execution NOT_RUN; step definitions not implemented.

  @AC012 @IP18 @FR01 @FR14 @FR32 @AT01 @AT13
  Scenario Outline: AC012 首次时区获取失败不猜测日期
    Given 清洁安装且首次设备日历返回<时区值>
    When 初始化本机数据
    Then 初始化结果为<预期>，未确定日期时不允许保存计划

    Examples:
      | rowId | 时区值 | 预期 |
      | valid | Asia/Shanghai | 固定该时区后进入真实空态 |
      | null | 空值 | 阻断初始化并提示重试 |
      | invalid | Invalid/Zone | 阻断初始化并提示重试 |

  @AC013 @IP22 @FR14 @FR16 @AT13
  Scenario: AC013 换设备时区不移动计划今天与历史
    Given 首次固定Asia/Shanghai，在2026-10-09 23:30上海时间已有循环记录和一次性安排
    When 将设备时区切为America/New_York并返回应用
    Then 所有页面仍按上海业务日期展示，历史位置和截止不变化

  @AC014 @IP06 @FR14 @AT13 @AT17
  Scenario Outline: AC014 公历加一天覆盖DST和月年边界
    Given DateAdapter使用<zone>与业务日期<日期>
    When 执行日历加一天并计算两个业务午夜间隔
    Then 得到<次日>且午夜间隔为<小时>小时

    Examples:
      | rowId | zone | 日期 | 次日 | 小时 |
      | spring | America/New_York | 2026-03-08 | 2026-03-09 | 23 |
      | fall | America/New_York | 2026-11-01 | 2026-11-02 | 25 |
      | leap | Asia/Shanghai | 2028-02-28 | 2028-02-29 | 24 |
      | year | Asia/Shanghai | 2026-12-31 | 2027-01-01 | 24 |

  @AC015 @IP20 @FR14 @FR15 @FR28 @AT18 @AT19
  Scenario: AC015 前台午夜重算不强制跳选中日期
    Given 当前业务日2026-10-09，日历选中10/08，10/09已保存结果
    When 前台跨至10/10午夜或应用从后台恢复
    Then 今天变为10/10，原今日恢复历史下标，选中日仍为10/08
