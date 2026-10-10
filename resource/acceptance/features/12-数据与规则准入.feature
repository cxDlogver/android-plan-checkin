# language: en
Feature: 数据与规则准入
  # Product execution NOT_RUN; step definitions not implemented.

  @AC108 @IP06 @FR14 @AT03 @AT18
  Scenario Outline: AC108 日期适配和初始化服务独立于页面验证
    Given 隔离日期服务使用IANA候选<候选>，存储初始无zone或已有Asia/Shanghai
    When 初始化、读取业务日，并切换设备zone后再次读取
    Then 初始化结果为<预期>，已有全局zone不会被设备变化覆盖

    Examples:
      | rowId | 候选 | 预期 |
      | valid | Asia/Shanghai | 成功并持久保存 |
      | null | null | 初始化失败且无zone |
      | invalid | Invalid/Zone | 初始化失败且无zone |

  @AC109 @IP09 @FR02 @FR03 @FR04 @FR05 @FR16 @FR23 @AT02 @AT03 @AT17 @AT21
  Scenario Outline: AC109 创建编辑和待生效规则服务的精确出口
    Given 规则服务使用10/09事实：fixed当前周二/四，weekly当前3，one_time创建10/07截止10/08，按<输入>选择对应计划类型
    When 执行CreatePlan或EditPlan并查询版本、当前值及pending值
    Then 得到<预期>，不追溯改变既有记录

    Examples:
      | rowId | 输入 | 预期 |
      | mask0 | 新建weekdayMask=0 | VALIDATION_FAILED且无新计划 |
      | weekday | 星期改周一/五 | 10/10生效版本 |
      | weekly | 3改5再改4 | 10/12只生效4 |
      | cancel | pending5保存回current3 | 取消pending，仍3 |
      | name | 只改名称，pending5 | 名称即时且pending5保留 |
      | paused | 暂停时改名称 | PAUSED且事实不变 |
      | due | 逾期截止10/08改10/15 | 立即待完成且旧版本保留 |

  @AC110 @IP10 @FR24 @FR25 @FR26 @FR27 @FR28 @AT17 @AT22 @AT23
  Scenario Outline: AC110 生命周期对账可在无页面时验证
    Given 上海Clock和合法阶段已准备，状态事件为<事件>
    When 调用管理命令与reconcile至<观察时点>并重复对账
    Then 状态和边界为<预期>，事件不重复

    Examples:
      | rowId | 事件 | 观察时点 | 预期 |
      | pause | 10/09申请暂停 | 10/10 00:00 | paused，旧stage结束10/10 |
      | resume | 10/09已暂停申请恢复 | 10/10 00:00 | active，新stage开始10/10 |
      | cancel | 10/09申请后当天取消 | 10/10 00:00 | 原active阶段未关闭 |
      | manual | 10/09立即归档 | 10/09提交后 | archived，边界真实提交时刻 |
      | natural | endOn=10/09 | 10/20离线重启 | archived，边界10/10 00:00 |

  @AC111 @IP11 @FR07 @FR08 @FR11 @FR12 @FR13 @AT04 @AT10 @AT11 @AT12 @AT13
  Scenario Outline: AC111 记录权限和原值服务不依赖确认页
    Given 运行阶段、目标日和记录种类为<事实>
    When 直接调用统一permission查询与提交/修改服务
    Then 权限与写入结果为<预期>，无页面旁路

    Examples:
      | rowId | 事实 | 预期 |
      | today | 今天ordinary且active | 当日修正允许 |
      | backfill | 当前stage昨天合法空日 | 新增backfill后READ_ONLY |
      | history | 昨天ordinary | READ_ONLY |
      | paused | 当前paused的历史空日 | PAUSED |
      | archived | 当前archived的历史空日 | ARCHIVED |
      | oldstage | 恢复后旧stage空日 | OLD_STAGE |
      | future | 目标明天 | DATE_INELIGIBLE |

  @AC112 @IP12 @FR10 @FR29 @FR31 @FR32 @AT09 @AT12 @AT23 @AT24 @AT28
  Scenario Outline: AC112 命令事务、跨日和重放服务出口
    Given 固定信封与最新事实已准备，服务输入为<条件>
    When 执行命令并捕获提交结果、receipt和事务前后逻辑摘要
    Then 返回<结果>，业务事实满足<写入>

    Examples:
      | rowId | 条件 | 结果 | 写入 |
      | day | 首次确认10/09保存10/10 | DAY_CHANGED | 无用户记录 |
      | replay | 同ID同摘要成功后重试 | OK replayed=true | 原记录和receipt各1 |
      | revision | 最新expectedPlanRevision、旧expectedRecordRevision | RECORD_CHANGED | 原值不变 |
      | duplicate | 不同ID争同日，expectedPlanRevision匹配最新 | RECORD_EXISTS | 同日仅1条 |
      | rollback | 提交前注入IO错误 | STORAGE_IO | 业务/receipt/revision全部回滚 |

  @AC113 @IP13 @FR17 @FR18 @AT14 @AT15 @AT20
  Scenario Outline: AC113 固定聚合和连续的数值出口
    Given 固定计划历史6成功/8有效分母，今天合法结果为<今日结果>
    When 直接查询fixedStatistics和currentStreak
    Then 分子分母为<比例>，skip变化为<跳过增量>

    Examples:
      | rowId | 今日结果 | 比例 | 跳过增量 |
      | pending | 空 | 6/8 | 0 |
      | success | success | 7/9 | 0 |
      | failure | failure | 6/9 | 0 |
      | skip | skip | 6/8 | 1 |

  @AC114 @IP14 @FR04 @FR19 @FR24 @FR25 @FR26 @FR28 @AT05 @AT16 @AT17 @AT23
  Scenario Outline: AC114 周聚合按完整自然周和真实终止边界计算
    Given 周目标3，当前或结束周事实为<事实>
    When 调用weeklyStatistics，分别观察该周结束前后
    Then 得到<预期>，不产生周空日每日失败

    Examples:
      | rowId | 事实 | 预期 |
      | over | 本周4成功日，未结束 | progress4/3 bar1，历史率不变 |
      | partial | 已有连续2，本周三暂停 | 结束前2，结束后0，排除周率分母 |
      | whole | 达标A、暂停整周B、达标C | B结束0，C结束1，B排除周率 |
      | natural | 周一运行至周日end且3/3 | 完整周，率分子分母各+1 |
      | manual | 同上但周日17点归档 | 部分周，率分母不增，周末连续0 |

  @AC115 @IP15 @FR05 @FR09 @FR20 @FR28 @AT06 @AT07 @AT08 @AT19 @AT23
  Scenario Outline: AC115 一次性终态与冻结截止的服务出口
    Given 10/09创建、10/10截止的一次性任务，操作为<操作>
    When 调用结果命令及classification/reconcile查询
    Then 业务日、分类和归档时点为<预期>

    Examples:
      | rowId | 操作 | 预期 |
      | ontime | 10/10登记当天完成 | business10/10，按时完成，10/11归档 |
      | late | 10/11登记当天完成 | business10/11，迟完成，10/12归档 |
      | history | 10/11补报10/09完成 | business10/09，按时完成，立即归档 |
      | fail | 10/11登记失败 | business10/11，failed，10/12归档 |
      | cancel | 10/11取消 | business10/11，cancelled，10/12归档 |

  @AC116 @IP16 @FR06 @FR14 @FR15 @FR16 @FR21 @FR22 @AT11 @AT18 @AT20 @AT25
  Scenario Outline: AC116 查询DTO的日集合、排序与分页出口
    Given 查询服务输入<数据集合>，所有读取经唯一执行器
    When 获取日历/今日/详情/历史DTO并在revision变化后再取
    Then 计数与集合为<预期>，同次查询快照一致

    Examples:
      | rowId | 数据集合 | 预期 |
      | mixed | 日期上两成功、一失败、一跳过、一固定未记录 | T5 C2，不完整2/5 |
      | weekly0 | 仅weekly且该日无记录 | T0 C0 |
      | weeklyskip | weekly已有skip | T1 C0 |
      | once | 10/10截止，10/11补报10/09完成 | 10/09为1/1；10/10旧安排移除 |
      | archive | 10/09归档未终结once且due10/10 | 10/10无安排 |
