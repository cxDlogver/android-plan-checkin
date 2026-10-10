# language: en
Feature: 统计回顾
  # Product execution NOT_RUN; step definitions not implemented.

  @AC062 @IP23 @FR17 @AT14 @AT15
  Scenario Outline: AC062 固定今天提交立即计入，跳过排除率分母
    Given 历史合法候选含6成功和2失败，今日应执行尚未提交
    When 今天处理为<处理>
    Then 详情固定历史显示<分数>与<百分比>

    Examples:
      | rowId | 处理 | 分数 | 百分比 |
      | pending | 未提交 | 6/8 | 75% |
      | success | success | 7/9 | 78% |
      | failure | failure | 6/9 | 67% |
      | skip | skip | 6/8 | 75%且skipCount+1 |
      | modify | 今天success再改failure | 6/9 | 67% |

  @AC063 @IP23 @FR12 @FR17 @AT14 @AT15
  Scenario: AC063 过去未知、补记和零分母有明确公式
    Given 有效过去两日均未记录，或有效两日均skip，均无未来统计候选
    When 回顾统计并给合法unknown日补success
    Then unknown进入分母，补记只增加分子，全skip暂无可计算记录

  @AC064 @IP23 @FR17 @FR19 @FR20 @FR22 @AT14 @AT19
  Scenario Outline: AC064 显示统计起止与分母集合分别处理
    Given 计划为<状态>，固定区间或周区间已知
    When 打开全部历史详情
    Then 显示截至规则为<截至>且不扩大分母

    Examples:
      | rowId | 状态 | 截至 |
      | running | 运行中 | today |
      | paused | 暂停 | today |
      | manual | 手动归档 | archiveOn |
      | natural | 自然循环到期 | endOn |
      | future | 未来未开始 | 尚未开始而非倒置日期 |

  @AC065 @IP23 @FR18 @AT15
  Scenario Outline: AC065 固定连续按应执行次数并按事件中断
    Given 10/07跳过，10/08成功，10/09今日应执行未提交，或非每日星期有合法间隔
    When 发生<事件>
    Then 当前连续为<连续>

    Examples:
      | rowId | 事件 | 连续 |
      | pending | 今日仍未提交 | 1 |
      | success | 今日success | 2 |
      | failure | 今日failure | 0 |
      | skip | 今日skip | 0 |
      | midnight | 无记录跨至次日 | 0 |
      | pause | 暂停实际生效 | 0 |
      | gap | 自选星期之间无安排日 | 不因间隔减少 |

  @AC066 @IP23 @FR04 @FR19 @AT05 @matrix_core
  Scenario: AC066 周目标超过目标仍显示实际天数且日唯一
    Given 完整当前周目标3，已有3个不同成功日期
    When 第四天成功并重复同日保存
    Then 进度4/3，进度条100%，当天不重复累计

  @AC067 @IP23 @FR19 @AT16
  Scenario: AC067 历史周率只纳入已结束完整周
    Given 已有4个结束完整周，其中3达标；当前完整周已3/3尚未结束
    When 当前查看再推进周结束，或测试另一个完整周0成功
    Then 当前仍3/4，当前达标周结束后4/5，0成功完整周未达标

  @AC068 @IP23 @FR19 @FR23 @FR24 @FR25 @FR26 @AT17 @AT23
  Scenario Outline: AC068 部分周排除率分母且周结束才中断
    Given 本周发生<部分原因>，此前连续为<此前连续>，后续可执行性为<后续执行>
    When 在本周结束前、结束后及后续观察日分别查看
    Then 连续依次为<结束前>、0、<后续连续>，部分周不进历史率分母

    Examples:
      | rowId | 部分原因 | 此前连续 | 后续执行 | 结束前 | 后续连续 |
      | starts | 周中开始 | 0 | 下一完整周运行并达标 | 0 | 1 |
      | pause | 周中暂停 | 2 | 下周一恢复并完整达标 | 2 | 1 |
      | resume | 周中恢复 | 0 | 下一完整周运行并达标 | 0 | 1 |
      | ends | 周中自然结束 | 2 | 已归档，只读不再执行 | 2 | 0 |
      | archive | 周日17:00手动归档 | 2 | 已归档，只读不再执行 | 2 | 0 |

  @AC069 @IP23 @FR19 @FR24 @FR25 @AT17
  Scenario: AC069 整周暂停不计率但结束时打断连续
    Given 完整达标A后周一暂停整周B，再于C周一恢复
    When B结束前后查看并让C完整达标至结束
    Then B结束前保留旧连续，结束归0，C结束连续1

  @AC070 @IP23 @FR19 @FR26 @FR28 @AT17 @AT23
  Scenario Outline: AC070 周日自然结束与即时归档完整周不同
    Given 本周自周一连续运行目标3并3/3，终止方式为<方式>
    When 到下周一回顾该周
    Then 该周判定为<完整性>

    Examples:
      | rowId | 方式 | 完整性 |
      | manual | 周日17:00手动归档 | partial |
      | natural | 结束日周日，次日00:00自然归档 | full达标 |
