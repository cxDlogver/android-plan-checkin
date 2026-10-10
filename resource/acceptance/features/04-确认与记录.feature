# language: en
Feature: 确认与记录
  # Product execution NOT_RUN; step definitions not implemented.

  @AC024 @IP21 @FR07 @FR08 @FR09 @FR10 @FR31 @AT09 @matrix_core
  Scenario Outline: AC024 点击结果仅预选，取消不生成记录
    Given 今天合法空项，记录结果为<结果>，尚未最终保存
    When 点击结果进入确认，填写备注并取消返回
    Then 确认页预选准确，取消后仍为未提交项

    Examples:
      | rowId | 结果 |
      | success | 循环成功 |
      | failure | 循环失败 |
      | skip | 循环跳过 |
      | completed | 一次性登记完成 |
      | cancelled | 一次性取消 |

  @AC025 @IP21 @FR07 @FR10 @FR31 @FR32 @AT01 @AT09 @matrix_core
  Scenario: AC025 最终确认普通记录后本机持久保存
    Given 2026-10-09运行每日计划无记录，确认页选成功并输入两行备注
    When 最终保存后关闭并重启应用
    Then 成功结果和两行备注按10/09显示，保存只发生一次

  @AC026 @IP21 @FR08 @FR11 @AT10 @AT12
  Scenario: AC026 不要做计划明确行为未发生与发生
    Given 10/09不要做计划尚未申报，没有自动监测
    When 当天先确认没有发生目标行为，后来修改为发生了目标行为
    Then 同一日期结果由成功改失败，次日仅可查看

  @AC027 @IP21 @FR10 @FR11 @FR13 @AT12 @AT14
  Scenario: AC027 普通当日修正加载当前值并保留首次原值
    Given 今天普通记录初值success和备注A，未归档
    When 修正为failure/备注B，再修正为skip/备注C后重新打开
    Then 页面显示最近已保存skip/C，原提交与最近修改分别可见

  @AC028 @IP21 @FR11 @FR23 @AT12 @AT21
  Scenario: AC028 无变化保存不制造修正或新revision
    Given 已有普通今天记录，或合法编辑页，所有输入等于当前显示值
    When 执行无变化保存
    Then 事实保持不变，不出现已修正标记

  @AC029 @IP21 @FR11 @FR12 @FR13 @AT12 @matrix_core
  Scenario Outline: AC029 历史与補记保存后的结果备注均只读
    Given 已有<记录类型>，所属业务日和当前日期已知
    When 从日历/详情/记录命令尝试改结果、备注或业务日期
    Then 修改被拒绝，事实日期和内容保持不变

    Examples:
      | rowId | 记录类型 |
      | past_ordinary | 昨日普通记录 |
      | today_backfill | 今天提交昨日的补记 |
      | archived_today | 归档计划今日普通记录 |
      | past_once | 一次性历史完成补报 |

  @AC030 @IP21 @FR03 @FR12 @FR15 @AT04 @AT11
  Scenario Outline: AC030 固定历史资格按目标星期判断
    Given 今天10/07，当前阶段周二/四fixed从10/01开始，无目标日记录
    When 尝试为<日期>首次登记
    Then 结果为<预期>

    Examples:
      | rowId | 日期 | 预期 |
      | valid_tue | 2026-10-06 | 允许补记并只读 |
      | invalid_wed | 2026-10-07 | 拒绝非应执行日 |
      | future_thu | 2026-10-08 | 拒绝未来 |

  @AC031 @IP21 @FR12 @FR24 @FR25 @FR26 @AT11 @AT22
  Scenario Outline: AC031 补记只限当前运行阶段合法空日
    Given 当前日期10/09，计划的目标日期属于<阶段情况>
    When 打开补记确认并通过记录服务请求新增
    Then 新增结果为<预期>

    Examples:
      | rowId | 阶段情况 | 预期 |
      | new_stage | 恢复10/07后合法10/08空日 | 允许一次补记 |
      | old_stage | 暂停前10/03空日，现已恢复 | 拒绝旧阶段 |
      | pause_gap | 10/04至10/06暂停空日 | 拒绝无效日 |
      | currently_paused | 当前暂停但10/03原本有效 | 拒绝暂停 |
      | archived | 当前归档且历史空日 | 拒绝归档 |
      | before_start | 早于startsOn | 拒绝未开始 |

  @AC032 @IP21 @FR10 @FR12 @FR31 @AT09
  Scenario: AC032 首次记录跨午夜拒绝旧保存再显式补记
    Given 10/09打开合法循环确认页，输入结果备注且confirmedToday=10/09
    When 10/10才点保存，再显式进入10/09补记确认并接受只读规则
    Then 旧保存提示日期变化且保留输入，新确认后才生成只读补记

  @AC033 @IP21 @FR10 @FR12 @FR24 @FR26 @FR28 @AT09 @AT22
  Scenario Outline: AC033 跨日后状态不合法不提供补记确认
    Given 10/09打开合法首次记录页，<核验日>目标已变成<状态>
    When 尝试旧保存并重新校验资格
    Then 保留输入并解释当前不可记录，不提供可保存的补记入口

    Examples:
      | rowId | 核验日 | 状态 |
      | pause | 10/10 | 已暂停 |
      | archive | 10/10 | 自动到期归档 |
      | oldstage | 10/12暂停后再恢复 | 目标属于已关闭旧阶段 |

  @AC034 @IP21 @FR11 @FR13 @FR31 @AT12
  Scenario: AC034 已有记录修改跨午夜直接只读
    Given 10/09普通记录修改页有未保存新结果和备注
    When 10/10点击保存
    Then 提示历史记录只读，不把修改转为补记

  @AC035 @IP21 @FR05 @FR09 @FR20 @FR28 @AT06 @AT07
  Scenario Outline: AC035 一次性完成按实际日期区分按时与迟完成
    Given 任务创建10/08、截止10/10，今天10/11，尚未终结
    When 登记完成并选择<实际日>后最终确认
    Then 结果为<预期>，记录业务日期与实际日一致

    Examples:
      | rowId | 实际日 | 预期 |
      | early | 2026-10-09 | 按时完成、历史补报立即归档 |
      | boundary | 2026-10-10 | 按时完成、历史补报立即归档 |
      | late | 2026-10-11 | 迟完成、普通终态 |

  @AC036 @IP21 @FR05 @FR09 @AT07 @matrix_core
  Scenario Outline: AC036 一次性完成日期范围和必填校验
    Given 任务创建10/08，今天10/11，完成页输入<实际日>
    When 尝试最终保存
    Then 日期校验为<预期>

    Examples:
      | rowId | 实际日 | 预期 |
      | before_created | 2026-10-07 | 拒绝 |
      | created | 2026-10-08 | 允许历史完成 |
      | future | 2026-10-12 | 拒绝 |
      | missing | 空值 | 拒绝必填 |

  @AC037 @IP21 @FR05 @FR09 @FR20 @FR28 @AT08
  Scenario Outline: AC037 一次性失败取消独立于循环跳过
    Given 10/11未终结任务截止10/10，今天已逾期
    When 确认<结果>并保存备注
    Then 显示明确<结果>终态，实际完成日期为空且次日归档

    Examples:
      | rowId | 结果 |
      | failed | 失败 |
      | cancelled | 取消 |

  @AC038 @IP21 @FR09 @FR11 @FR20 @AT12
  Scenario: AC038 一次性三结果同日可改但业务日期截止固定
    Given 10/11普通迟完成结果引用10/10截止，尚未归档
    When 当天依次修正失败、取消、完成，并尝试改变记录日期或截止
    Then 三结果可修正，完成恢复实际日10/11，日期与截止不能移动

  @AC039 @IP21 @FR09 @FR10 @FR31 @AT09
  Scenario Outline: AC039 一次性首次跨日不自动补报失败取消
    Given 10/09一次性确认页选择<结果>，10/10尚未保存
    When 执行旧保存后重新确认
    Then 旧命令拒绝，完成可合法显式补报，失败取消只能确认新today

    Examples:
      | rowId | 结果 |
      | completed | 完成且实际10/09 |
      | failed | 失败 |
      | cancelled | 取消 |

  @AC040 @IP21 @FR10 @FR31 @AT09 @AT24
  Scenario: AC040 重复同命令及跨日成功重试只返回一次事实
    Given 一次保存已经commit且原调用会话持有相同信封，可能尚未收到响应
    When 同内容双击或在次日7天窗口内重试原commandId
    Then 返回既有成功而非日期变化，事实不重复

  @AC041 @IP21 @FR10 @FR11 @AT24
  Scenario Outline: AC041 不同命令争抢同日或旧revision不静默覆盖
    Given 两个入口读取同一计划版本，目标为<冲突类型>
    When 前一命令成功后提交后一命令
    Then 后一命令返回冲突并提示加载最新事实

    Examples:
      | rowId | 冲突类型 |
      | duplicate_cycle | 循环同日两条首次记录 |
      | duplicate_once | 一次性两个首次终态 |
      | stale_record | 旧记录revision修正 |
      | stale_plan | 旧计划revision管理/记录 |

  @AC042 @IP12 @FR10 @FR29 @AT24
  Scenario Outline: AC042 命令ID复用、过期和删除重放被拒绝
    Given 已有命令事实处于<凭据情况>
    When 提交相关旧信封
    Then 返回<错误>且不改变目标事实

    Examples:
      | rowId | 凭据情况 | 错误 |
      | reused | 相同commandId但不同内容 | COMMAND_ID_REUSED |
      | expired | issuedAt已满7×24h | COMMAND_EXPIRED |
      | expired_cleaned | 超过7天且receipt已清理 | COMMAND_EXPIRED |
      | removed | 目标已永久删除且receipt墓碑有效 | TARGET_REMOVED |
      | clock | issuedAt晚于now | CLOCK_CHANGED |

  @AC043 @IP21 @FR10 @FR29 @FR31 @FR32 @AT24
  Scenario Outline: AC043 写失败或空间不足保留输入并完整回滚
    Given 目标事实已知，表单包含新结果备注，故障发生在commit前
    When 最终保存时遇到<故障>
    Then 界面明确未确认保存，输入与原事实保留并允许重试

    Examples:
      | rowId | 故障 |
      | io | 存储IO异常 |
      | full | 空间不足 |
      | busy | SQLite busy |
      | archive_fail | 归档/永久删除事务失败 |

  @AC044 @IP21 @FR10 @FR31 @FR32 @AT01 @AT24
  Scenario Outline: AC044 commit前后进程中断恢复事实而非草稿
    Given 最终保存正处于<中断点>，未保存输入仅在当前会话
    When 杀死应用并重新启动
    Then 重启结果为<预期>，不恢复草稿或自动重提交

    Examples:
      | rowId | 中断点 | 预期 |
      | before_commit | commit前 | 原事实保持 |
      | after_commit | commit后返回前 | 已提交事实保留 |

  @AC102 @IP12 @FR10 @FR29 @FR32 @AT24
  Scenario: AC102 重试窗口边界与凭据限批清理
    Given 命令issuedAt已知，存在201条过期receipt和有效墓碑，无用户文本
    When 分别在窗口结束前/结束时重试，并执行一次空闲清理
    Then 窗口前允许相同命令重试，达到7天拒绝，单批至多200行

  @AC105 @IP21 @FR07 @FR09 @FR10 @FR31 @AT09 @AT24 @AT26
  Scenario: AC105 未选结果不能最终保存且提交中禁重复操作
    Given 记录确认页尚未选有效结果，或提交事务正处理中
    When 尝试保存、换结果或再次按保存
    Then 未选时不能提交，处理中禁用且成功只在落盘后反馈
