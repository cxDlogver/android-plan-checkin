# language: en
Feature: 创建与编辑
  # Product execution NOT_RUN; step definitions not implemented.

  @AC016 @IP19 @FR02 @FR03 @FR04 @FR05 @AT02 @AT03 @matrix_core
  Scenario: AC016 新建默认值和星期未选状态
    Given 尚无表单草稿且当前业务日为2026-10-09
    When 打开新建页并依次查看固定、每周、一次性类型
    Then 固定默认不选星期，需用户选择后保存
    And 各类型默认值准确

  @AC017 @IP19 @FR02 @FR10 @FR31 @AT02
  Scenario Outline: AC017 文本码点边界与单行名称
    Given 表单其他必填已合法，输入<字段>为<样本>
    When 执行最终保存
    Then 得到<结果>，错误时输入仍可继续编辑

    Examples:
      | rowId | 字段 | 样本 | 结果 |
      | blank_name | 名称 | 全空白 | 拒绝非空校验 |
      | trim_name | 名称 | 首尾空白包围的读书 | 保存为读书 |
      | 80_name | 名称 | 80个码点含emoji | 允许保存 |
      | 81_name | 名称 | 81个码点 | 拒绝超长 |
      | newline_name | 名称 | 内部换行 | 拒绝多行 |
      | 1000_desc | 说明 | 1000码点含换行 | 允许保存 |
      | 1001_desc | 说明 | 1001码点 | 拒绝超长 |
      | empty_note | 备注 | 空串 | 允许保存 |
      | 2000_note | 备注 | 2000码点 | 允许保存 |
      | 2001_note | 备注 | 2001码点 | 拒绝超长 |

  @AC018 @IP19 @FR02 @FR03 @FR04 @FR05 @AT02
  Scenario: AC018 切换类型保留共通字段并拒绝隐藏字段混入
    Given 固定表单有名称说明和星期，尚未保存
    When 切到一次性并确认清除不适用值，再切到每周后保存
    Then 共通名称说明保留，只保存每周类型适用字段

  @AC019 @IP19 @FR02 @FR03 @FR04 @AT03
  Scenario Outline: AC019 循环日期不得过去或倒置
    Given 创建日为2026-10-09，循环开始为<开始>，结束为<结束>
    When 提交有效其他字段的新计划
    Then 保存结果为<预期>

    Examples:
      | rowId | 开始 | 结束 | 预期 |
      | past | 2026-10-08 | 空 | 拒绝过去开始 |
      | today | 2026-10-09 | 空 | 允许 |
      | future | 2026-10-10 | 2026-10-11 | 允许且未开始 |
      | reversed | 2026-10-10 | 2026-10-09 | 拒绝结束早于开始 |
      | same | 2026-10-09 | 2026-10-09 | 允许当天执行 |
      | invalid_date | 2026-02-30 | 空 | 拒绝非法公历日 |

  @AC020 @IP19 @FR03 @AT02 @AT04
  Scenario: AC020 固定星期选择与每日摘要一致
    Given 新建fixed默认未选星期
    When 使用每日快捷全选，再取消周日，随后取消剩余全部星期
    Then 每日全选和自选摘要准确，全部未选时不能保存

  @AC021 @IP19 @FR04 @AT02 @AT05
  Scenario Outline: AC021 每周目标只接受1至7整数
    Given weekly其他字段合法，输入目标<目标>
    When 提交计划
    Then 得到<预期>

    Examples:
      | rowId | 目标 | 预期 |
      | one | 1 | 允许 |
      | seven | 7 | 允许 |
      | zero | 0 | 拒绝 |
      | eight | 8 | 拒绝 |
      | decimal | 3.5 | 拒绝 |
      | empty | 空值 | 拒绝 |

  @AC022 @IP19 @FR02 @FR21 @FR22 @AT02 @AT19
  Scenario: AC022 同名计划保持独立且创建成功导航详情
    Given 一个名为读书的fixed已存在，准备同名weekly计划
    When 保存第二个计划并返回今日和计划列表
    Then 出现两个独立计划，新建成功先显示新计划详情

  @AC023 @IP19 @FR23 @FR24 @FR26 @FR28 @AT19 @AT21
  Scenario Outline: AC023 暂停归档和不可变字段拒绝编辑
    Given 计划具有<条件>
    When 从管理页或应用命令尝试<修改>
    Then 编辑被拒绝并显示对应只读理由

    Examples:
      | rowId | 条件 | 修改 |
      | paused | 暂停循环 | 名称或规则 |
      | archived | 已归档 | 任意字段 |
      | immutable | 运行循环 | 类型、方向、开始日或时区 |
      | terminal_due | 普通一次性终态未归档 | 截止日期 |

  @AC101 @IP19 @FR02 @FR05 @AT02 @AT03 @AT07
  Scenario Outline: AC101 一次性创建截止必填且没有循环字段
    Given 10/09创建one_time，名称合法，截止输入<截止>
    When 最终保存任务
    Then 结果为<预期>，仅保存一次性字段

    Examples:
      | rowId | 截止 | 预期 |
      | today | 2026-10-09 | 允许 |
      | future | 2026-10-10 | 允许 |
      | past | 2026-10-08 | 拒绝 |
      | empty | 空值 | 拒绝必填 |

  @AC107 @IP19 @FR02 @FR05 @FR31 @AT03 @AT09
  Scenario: AC107 新建表单跨日重新校验且不自动挪日期
    Given 10/09新建页选择startsOn或dueOn=10/09，尚未提交且名称说明已输入
    When 10/10执行保存
    Then 过去的开始或截止被拒绝，原输入保留等待用户选择

  @AC120 @IP19 @FR02 @FR03 @FR04 @FR05 @AT02 @AT03 @AT05 @AT07 @AT25 @AT26 @matrix_core
  Scenario Outline: AC120 三类合法新建在八组合最终保存
    Given 当前业务10/09，表单选择<类型>、合法名称说明和<规则>，新建fixed初始未选且由用户明确选择
    When 确认合法输入并最终保存，进入新计划详情后返回列表和今日
    Then 只生成1个<类型>计划及对应有效初始规则，可从来源页找到

    Examples:
      | rowId | 类型 | 规则 |
      | fixed | fixed | 手动周二/四，开始10/09 |
      | weekly | weekly | 目标3，开始10/09 |
      | one | one_time | 截止10/10，仅do |
