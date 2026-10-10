# language: en
Feature: 页面与异常
  # Product execution NOT_RUN; step definitions not implemented.

  @AC082 @IP18 @FR01 @FR32 @AT01 @AT24 @matrix_core
  Scenario Outline: AC082 初始化加载和读库错误不伪装空态
    Given 首次启动处于<数据条件>
    When 等待初始化或打开主页面
    Then 页面为<预期>

    Examples:
      | rowId | 数据条件 | 预期 |
      | loading | 读取尚未完成 | 加载态 |
      | empty | 成功读到空库 | 真实空态和创建入口 |
      | error | 初始化/读库失败 | 无法读取本机数据及重试 |

  @AC083 @IP20 @FR06 @FR07 @FR08 @FR09 @AT09 @AT14 @AT19 @matrix_core
  Scenario: AC083 今日四分区包含全部未终结一次性
    Given 测试有今日fixed空项、weekly达标项、未来/逾期一次性和今日记录
    When 打开今日页并刷新两次
    Then 固定待处理、本周可记录、截止事项、已记录分区正确无重复

  @AC084 @IP20 @FR06 @FR10 @FR31 @AT09 @AT14
  Scenario: AC084 保存成功就地反馈下次刷新才归已记录
    Given 今日原分区有空项，用户已确认记录
    When 完成落盘后留在原页，再离开返回或手动刷新
    Then 先原位置显示真实保存结果，随后仅在已记录分区出现一次

  @AC085 @IP24 @FR21 @FR22 @FR28 @AT19 @matrix_core
  Scenario: AC085 计划列表筛选状态与稳定排序可找到全部历史
    Given 包含未来未开始、暂停、归档、自然结束、普通终态未归档及逾期任务
    When 遍历运行、暂停、已归档列表并打开详情
    Then 每个计划位于正确状态且状态/结果明确可辨

  @AC086 @IP23 @FR16 @FR22 @AT18 @AT20 @AT21
  Scenario: AC086 历史按当时规则倒序分页不漏项
    Given 计划有跨规则版本历史及超过一页记录，查询后有合法新事实或删除
    When 分页查看、补记合法旧日并再次分页或继续旧游标
    Then 旧日期按旧规则，历史倒序且revision变化重置游标

  @AC087 @IP18 @FR22 @FR29 @FR32 @AT20
  Scenario: AC087 目标删除或读失败不能从旧缓存继续写
    Given 详情或记录页持有旧DTO，目标随后永久删除或数据库读失败
    When 继续操作或返回来源
    Then 明确目标不可用或读取错误，不能提交旧对象

  @AC088 @IP18 @FR31 @AT09 @AT26
  Scenario Outline: AC088 草稿退出与Back优先级
    Given 表单输入与脏状态按参数准备，当前<前台层>
    When 按系统Back或尝试离开表单
    Then 行为为<预期>，数据仍未提交

    Examples:
      | rowId | 前台层 | 预期 |
      | keyboard | 键盘打开 | 先关键盘 |
      | modal | 日期/筛选弹层打开 | 先关弹层 |
      | dirty | 无浮层且有变更 | 继续编辑/放弃确认 |
      | clean | 无变更 | 直接返回 |

  @AC089 @IP25 @FR30 @AT01 @AT27
  Scenario Outline: AC089 本机设置显示真实版本和无备份边界
    Given 应用为免登录本机版，原生版本字段为<版本条件>
    When 打开设置并遍历全部可见功能入口
    Then 固定时区、本机说明与<版本展示>准确

    Examples:
      | rowId | 版本条件 | 版本展示 |
      | valid | 原生字段可取 | 实际versionName/versionCode |
      | null | 原生字段null | 版本不可用 |

  @AC106 @IP23 @FR09 @FR20 @FR22 @AT06 @AT07 @AT08 @AT19
  Scenario: AC106 一次性回顾显示实际日期而非固定完成率
    Given 一次性已有completed/failed/cancelled结果，业务日期和提交时刻不同或已修正
    When 从今日、列表和日历进入详情及只读记录
    Then 各入口显示同一结果、截止、实际日、提交与备注
