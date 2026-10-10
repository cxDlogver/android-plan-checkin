# language: en
Feature: 日历与筛选
  # Product execution NOT_RUN; step definitions not implemented.

  @AC071 @IP22 @FR14 @FR15 @AT18 @AT25 @matrix_core
  Scenario Outline: AC071 非今日每格仅一个汇总下标
    Given 选中非今日日期，U(d)的完成数为<C>且总数为<T>
    When 查看日历格和未筛选明细
    Then 唯一标记为<标记>，标题和逐项数量一致

    Examples:
      | rowId | C | T | 标记 |
      | all | 5 | 5 | 绿色✓ |
      | partial | 2 | 5 | 黄色2/5 |
      | none_done | 0 | 1 | 黄色0/1 |
      | empty | 0 | 0 | 空白 |
      | large | 99 | 100 | 完整黄色99/100 |

  @AC072 @IP22 @FR14 @AT18 @AT25 @matrix_core
  Scenario: AC072 今天浅色填充与选中边框独立
    Given 今天10/09可能全部完成或部分完成，10/08为其他选中日
    When 切换选中日并查看今日格
    Then 今日始终浅色填充加粗日期，无点、勾或分数

  @AC073 @IP22 @FR14 @FR17 @AT15 @AT18
  Scenario: AC073 日历分母与固定历史分母不能混用
    Given 日历同日三个计划为2成功+1跳过；另有一个fixed计划跨三日的历史候选也是2成功+1跳过
    When 查看全局选日及固定历史统计
    Then 日历2/3，固定率2/2并单列跳过1

  @AC074 @IP22 @FR04 @FR14 @FR15 @AT05 @AT18
  Scenario Outline: AC074 周目标只把已有记录加入每日集合
    Given 一周目标3的有效历史空日无其他计划，当周已达标
    When 查看空日并随后补记为<结果>
    Then 空日T=0，保存后该日T=1且完成标记按结果判定

    Examples:
      | rowId | 结果 |
      | success | success |
      | failure | failure |
      | skip | skip |

  @AC075 @IP22 @FR05 @FR09 @FR14 @AT06 @AT18
  Scenario: AC075 一次性终态替代截止安排且按业务日归属
    Given 一次性截止10/10，今天10/11，任务创建不晚于10/09
    When 登记实际10/09完成或将未终结截止延至10/15
    Then 完成仅10/09一项，或未终结安排仅10/15一项

  @AC076 @IP22 @FR14 @FR26 @AT18 @AT23
  Scenario Outline: AC076 手动归档一次性只保留过去截止项
    Given 10/09手动归档尚无结果的一次性任务，当前截止为<截止>
    When 查看截止日和未来月的集合
    Then 截止安排为<预期>

    Examples:
      | rowId | 截止 | 预期 |
      | past | 2026-10-08 | 保留10/08未完成1项 |
      | today | 2026-10-09 | 取消10/09空安排 |
      | future | 2026-10-10 | 取消10/10未来安排 |

  @AC077 @IP22 @FR14 @FR15 @AT18
  Scenario: AC077 未来固定截止安排只读0/T
    Given 未来日含合法fixed和未终结一次性截止，没有记录
    When 选中未来日并尝试新增记录
    Then 日期格黄色0/T、明细说明未来安排且不可提交

  @AC078 @IP22 @FR15 @AT18 @matrix_core
  Scenario: AC078 筛选只改变明细不改变全局总数
    Given 10/08集合5项，其中2完成，3失败/跳过/未记录
    When 依次选择全部、已完成、未完成
    Then 列表分别5、2、3项，标题仍10/08·5项计划、日期格仍2/5

  @AC079 @IP22 @FR15 @FR31 @AT18 @AT26
  Scenario: AC079 切日重置筛选，记录返回恢复并重算数量
    Given 当前月份选历史日、filter=incomplete、已知滚动位置，存在合法补记项
    When 进入记录保存并返回同日，再切另一日或回今天
    Then 同日保留月份/日期/筛选/滚动且数量更新，新选日重置all

  @AC080 @IP22 @FR15 @FR12 @AT11 @AT18 @AT26
  Scenario: AC080 筛选关闭空结果与独立周补记区准确
    Given 历史日有全未完成主项和合法weekly空日候选，当前filter=all
    When 展开筛选后Back/点外关闭，再选择已完成
    Then 关闭未改变all，已完成空列表有解释，周补记区仍可见

  @AC081 @IP22 @FR14 @FR16 @AT18 @AT25
  Scenario: AC081 月份跨格和回今天使用真实完整日期
    Given 当前月含6行42个可见格和跨月日期
    When 切上/下月、选跨月日期后回今天
    Then 跨月日号弱色且日期不串月，回今天选当前月今天
