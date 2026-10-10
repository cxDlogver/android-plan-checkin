# language: en
Feature: 生命周期
  # Product execution NOT_RUN; step definitions not implemented.

  @AC045 @IP24 @FR24 @FR27 @AT22 @matrix_core
  Scenario: AC045 暂停明天生效且今天仍可记录
    Given 10/09循环运行中，无待生效状态申请
    When 确认明天10/10暂停，分别在10/09和10/10查看或提交
    Then 10/09仍运行，10/10才暂停停止新要求

  @AC046 @IP24 @FR25 @FR12 @AT22 @matrix_core
  Scenario: AC046 恢复明天开启新阶段但不补旧日期
    Given 10/09循环已暂停，10/03曾有效但无记录
    When 确认10/10恢复，10/11再尝试记录10/03、暂停日和10/10
    Then 恢复申请当天仍暂停，次日运行
    And 仅新阶段10/10合法空日可补记

  @AC047 @IP24 @FR24 @FR25 @FR27 @AT22
  Scenario Outline: AC047 生效前取消申请不改变执行阶段
    Given 10/09已申请明天<申请>，尚未到effectiveAt
    When 确认取消该申请并推进到10/10
    Then 申请被标取消，原有效状态持续且没有新阶段事件

    Examples:
      | rowId | 申请 |
      | pause | 暂停 |
      | resume | 恢复 |

  @AC048 @IP24 @FR24 @FR25 @FR27 @AT22
  Scenario: AC048 跨日已生效申请不可取消且旧日期确认不能漂移
    Given 10/09确认页显示10/10生效，或待取消事件在10/10已生效
    When 跨到10/10后提交旧申请确认或取消
    Then 过期确认需要重新确认具体日期，已生效事件不能取消

  @AC049 @IP24 @FR26 @FR29 @AT23 @matrix_core
  Scenario Outline: AC049 运行暂停删除均立即归档而保留全部历史
    Given 计划当前为<状态>，包含已保存结果和备注
    When 选择删除并确认移入归档
    Then 计划立即移至归档，今日移除但历史仍可查看

    Examples:
      | rowId | 状态 |
      | running | 运行中 |
      | paused | 暂停 |

  @AC050 @IP24 @FR14 @FR17 @FR26 @AT23
  Scenario Outline: AC050 手动归档当天保留记录并取消空要求
    Given 10/09固定应执行项状态为<今日记录>
    When 10/09立即归档并在10/10回顾10/09
    Then 当日集合与固定历史统计为<预期>

    Examples:
      | rowId | 今日记录 | 预期 |
      | recorded | success已提交 | 保留完成项和原分母 |
      | unrecorded | 没有记录 | 无当日执行项/分母/unknown |

  @AC051 @IP24 @FR17 @FR19 @FR28 @AT19 @AT23
  Scenario Outline: AC051 自然结束包含末日并在次日归档
    Given 运行循环结束日10/09，末日符合当时规则且<末日记录>
    When 10/09查看，再推进到10/10
    Then 末日仍有资格，次日自动归档且末日要求保留

    Examples:
      | rowId | 末日记录 |
      | empty | 空白 |
      | recorded | success |

  @AC052 @IP21 @FR09 @FR20 @FR28 @AT06 @AT08 @AT19
  Scenario Outline: AC052 一次性普通终态与历史补报归档边界不同
    Given 任务于10/11提交<终态类型>
    When 保存后立即查看，再到10/12查看
    Then 归档时点为<归档规则>，保存的业务日期不移动

    Examples:
      | rowId | 终态类型 | 归档规则 |
      | ordinary_complete | 实际10/11完成 | 10/12午夜 |
      | ordinary_failed | 失败或取消 | 10/12午夜 |
      | backfill | 实际10/09历史完成 | 10/11保存now立即 |

  @AC053 @IP24 @FR24 @FR25 @FR27 @FR28 @FR32 @AT19 @AT22 @AT24
  Scenario: AC053 长时间离线对账使用原边界且归档优先
    Given 结束10/09与恢复申请同于10/10午夜，应用已关闭多天
    When 10/20重启并连续执行两次对账
    Then 计划归档边界仍10/10，恢复不执行且不产生第二归档

  @AC054 @IP24 @FR10 @FR28 @FR32 @AT09 @AT24
  Scenario: AC054 拒绝旧提交不回滚独立合法对账
    Given 10/09确认页未提交，计划10/09自然结束，当前已10/10
    When 提交旧确认命令并随后重查状态
    Then 旧记录不写入，合法10/10自动归档已持久生效

  @AC055 @IP24 @FR02 @FR17 @FR19 @FR24 @FR26 @AT03 @AT14 @AT19
  Scenario: AC055 开始前管理不产生负执行区间
    Given 10/09创建10/15才开始的循环计划
    When 开始前暂停或立即归档后查看详情和日历
    Then 没有虚构历史要求或倒置统计区间

  @AC056 @IP24 @FR26 @FR29 @AT23 @matrix_core
  Scenario: AC056 归档后永久删除取消保留确认才清空
    Given 已归档计划有两条循环记录、备注、规则和原值信息
    When 打开永久删除先取消，再次打开并确认
    Then 取消保持历史，确认后该计划全部历史在所有查询消失
