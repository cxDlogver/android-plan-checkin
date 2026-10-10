# language: en
Feature: 矩阵与视觉
  # Product execution NOT_RUN; step definitions not implemented.

  @AC090 @IP27 @FR07 @FR08 @FR14 @FR31 @AT25 @AT26
  Scenario: AC090 金属材质字体边距与结果语义
    Given 指定API与100%字号、已加载design-tokens与Pen参考画板
    When 查看今日、表单、详情、结果选择和日历
    Then 低圆角金属表面、粗标题和状态符号文字一致可辨

  @AC091 @IP27 @FR02 @FR03 @FR04 @FR05 @FR14 @FR31 @FR32 @AT25 @AT26 @AT28
  Scenario Outline: AC091 8组合读回与核心操作逐配置验收
    Given 设备为API<API>、宽<宽>dp、字号<字号>且安装目标构建
    When 读回设备配置并执行全部标记matrix_core的创建/记录/日历/状态流程
    Then 各核心断言通过，无裁切、横向溢出或主要操作不可达

    Examples:
      | rowId | API | 宽 | 字号 |
      | M1 | 29 | 360 | 1.0 |
      | M2 | 29 | 360 | 2.0 |
      | M3 | 29 | 393 | 1.0 |
      | M4 | 29 | 393 | 2.0 |
      | M5 | 36 | 360 | 1.0 |
      | M6 | 36 | 360 | 2.0 |
      | M7 | 36 | 393 | 1.0 |
      | M8 | 36 | 393 | 2.0 |

  @AC092 @IP27 @FR14 @FR15 @AT25
  Scenario: AC092 六行日历和大数字号不截断
    Given 日历含六行、0/1、2/5和99/100，并使用M1–M8矩阵
    When 选择日期、展开筛选并查看分数全部内容
    Then 七列对齐且完整显示分子分母，命中区至少48dp

  @AC093 @IP27 @FR31 @FR32 @AT26
  Scenario Outline: AC093 键盘系统栏与两种导航Back可用
    Given API29/36、大小字号设备采用<导航>，表单有长备注和日期弹层
    When 打开键盘、滚动至保存、关闭弹层和Back返回
    Then 内容不被系统栏键盘遮住，Back优先级正确

    Examples:
      | rowId | 导航 |
      | gesture | 手势导航 |
      | three_button | 三键导航 |

  @AC094 @IP27 @FR07 @FR13 @FR14 @FR15 @FR31 @AT26
  Scenario: AC094 TalkBack朗读完整日期结果权限及筛选数量
    Given TalkBack开启，包含今天、未来、已选日期、历史只读、筛选和各结果
    When 遍历焦点并执行一次选择、保存或查看操作
    Then 自然中文语义准确且所有主操作可访问
