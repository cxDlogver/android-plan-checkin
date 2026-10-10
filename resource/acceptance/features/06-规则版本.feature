# language: en
Feature: 规则版本
  # Product execution NOT_RUN; step definitions not implemented.

  @AC057 @IP19 @FR03 @FR16 @FR23 @AT21
  Scenario: AC057 固定星期明天生效且不改旧资格
    Given 10/09 fixed当前周二/四，当前阶段10/08是合法历史空日
    When 10/09改为周五并保存，补记10/08且查看10/09及10/10后规则
    Then 旧日仍按周二/四，变更从10/10生效而不创造今日周五要求

  @AC058 @IP19 @FR04 @FR19 @FR23 @AT17 @AT21
  Scenario Outline: AC058 周目标严格下周一生效并以最后值为准
    Given 本周目标3，<编辑日>先改5再改4，尚未到下周一
    When 保存两次并查看本周与<生效日>后的目标
    Then 本周仍3，下周仅4生效，被替代5保留为取消版本

    Examples:
      | rowId | 编辑日 | 生效日 |
      | friday | 2026-10-09 | 2026-10-12 |
      | monday | 2026-10-12 | 2026-10-19 |

  @AC059 @IP19 @FR23 @AT21
  Scenario: AC059 pending优先显示且回current取消该字段
    Given weekly当前3、待生效5，或fixed有待生效星期
    When 重开编辑先只改名称，再将规则字段保存回当前有效值
    Then 初值显示pending，只改名称保留申请，回current取消该字段

  @AC060 @IP19 @FR05 @FR23 @FR28 @AT21
  Scenario Outline: AC060 结束截止即时保存及逾期延期
    Given 10/11正在运行的循环或未终结一次性，编辑<字段>为<新值>
    When 最终保存并重查今日/详情/日历
    Then 行为为<预期>

    Examples:
      | rowId | 字段 | 新值 | 预期 |
      | end_today | 循环结束 | 2026-10-11 | 今日仍有效次日归档 |
      | end_past | 循环结束 | 2026-10-10 | 拒绝过去 |
      | due_extend | 逾期一次性截止10/10 | 2026-10-15 | 即时待完成，安排移动 |
      | due_past | 一次性截止 | 2026-10-10 | 拒绝过去 |

  @AC061 @IP19 @FR23 @FR31 @AT21 @AT26
  Scenario: AC061 规则生效日期确认跨边界需重新确认
    Given 固定星期确认明天生效，或周日N编辑确认下周一生效
    When 跨业务日导致具体生效日期变化后保存
    Then 返回确认过期，保留输入并显示新的生效日期
