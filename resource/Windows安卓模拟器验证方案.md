# Windows 安卓模拟器验证方案

> 日期：2026-10-09（Asia/Shanghai）  
> 应用：React Native/Expo、本机免登录、完全离线  
> 目标：模拟器验证＋无需 Metro 的独立 APK  
> 当前：依赖元数据与严格锁解析已通过；模拟器/自动化环境已安装并实测PASS；应用完整安装、原生构建、产品验收及APK运行NOT_RUN

## 1. 可行性与现状

Windows可开发、编译、运行安卓应用。本机采用官方CLI工具安装SDK、Emulator及系统镜像，已创建并启动API29/36 AVD，无需完整Studio即可运行模拟器。[Android Emulator](https://developer.android.com/studio/run/emulator)、[CLI工具](https://developer.android.com/studio#command-tools)

已复用D:\xiang\CX_application\1_Configuration_Files\JAVA\jdk-17.0.1；Node24.21.0、SDK/ADB、Emulator、镜像/AVD及Appium/UiAutomator2放在D:\xiang\CX_application\1_Configuration_Files\Android-AI。JAVA_HOME/PATH等通过项目脚本在当前终端加载；全局Node保持原值。精确版本、启动命令及实测截图见[环境配置记录](安卓AI验收环境配置记录-20261009.md)。

WHPX实际加速检查PASS；两套4核/4GiB、393dp AVD串行启动成功，原生定位/点击/输入/Back/截图均PASS。本轮续配再次验证API36，增加一键启动/停止及服务复用，结束时保留API36与Appium后台运行；实际运行状态见工具目录logs/runtime-state.json。启动与编译前重查空闲内存，保持单个AVD。

## 2. 准备

Windows 官方要求 64 位 Windows 10 或更新、CPU 虚拟化；Studio＋模拟器至少 16GB RAM，推荐 32GB。安装时再次核对 CPU、显卡、磁盘要求。[安装要求](https://developer.android.com/studio/install)

推荐 WHPX，加速需 Intel VT-x / AMD-V（SVM）及 BIOS/系统配置。AEHD 将于 2026-12-31 停用，新环境优先 WHPX。[加速指南](https://developer.android.com/studio/run/emulator-acceleration)

1. 核对系统、内存、磁盘、虚拟化。
2. SDK Platform、Build Tools、Platform Tools和Emulator已用CLI准备；Studio为可选开发界面。
3. 独立Node24.21.0、pnpm10.28.2、JDK17、Platform36及Build Tools36已准备；NDK/CMake留待工程按实际版本安装。minSdk29，生成后记录Gradle/AGP/Kotlin并实际构建。
4. 终端加载resource/scripts/Use-AndroidAI.ps1配置SDK/PATH。
5. WHPX已实测可用，无需此次修改BIOS或系统组件。
6. 两套AVD已创建；按环境记录中的脚本重新启动与等待就绪。
7. 环境检查已通过；应用开发时安装实际APK再执行产品验收。

## 3. 构建和 APK

使用包含实际原生依赖的Expo Development Build。数据采用普通SQLite与应用私有目录；已确认关闭系统云备份及设备迁移，需检查manifest、备份XML和实际数据库/WAL/SHM目录。Expo Go不能替代独立安装包验证。

应用工程就绪后，从应用目录用 pnpm exec expo run:android 构建，JS 开发用 pnpm exec expo start --dev-client；原生配置变化后重建。[Expo 本地开发](https://docs.expo.dev/guides/local-app-development/)

Expo本地开发文档通过Android Studio引导SDK与Java环境配置；本机当前CLI SDK/JDK及模拟器已就绪，Expo/Gradle应用构建在P1实际验证，与EAS --local是不同路径。[Expo CLI](https://docs.expo.dev/more/expo-cli/)、[Android命令行构建](https://developer.android.com/build/building-cmdline)

独立APK内置JS、字体及必要资源，关闭Metro、飞行模式也可首次创建/记录/回顾。Windows本地Expo CLI＋Gradle Wrapper构建，长期正式release签名、固定包名和递增versionCode；覆盖安装验证保留历史。具体维护补丁和证书在首个工程固化，签名材料仓库外保管，不写共享文档。

本机版无需 API、Docker、短信或推送服务。

应用工程首次生成真实锁文件后，后续采用pnpm install --frozen-lockfile、expo install --check和Android打包检查。评审目录清单/锁文件只是本轮依赖图证据，不能当作已经安装的应用。SDK57 prebuild默认重新生成原生目录，先保存原生修改并转为配置/插件，明确保留目录时使用--no-clean并核对合并。SDK/AVD继续在D盘；删除指定归档后F盘约36.60GiB空闲，原空间阻碍解除，应用可继续在当前项目目录准备。原生工程准备时重查NDK/Gradle与构建产物占用。

最小原生包先验证SQLite事务、固定IANA时区/Intl、路由及手势动画、静态400/600/700中文字体、金属渐变/内外影、API36系统栏与键盘；development和release均执行。字体格式验证、锁解析通过不等于这些原生场景已经通过。

SDK57发布模板的Gradle9.3.1/AGP8.12满足已核实最低要求，但8.12不在Gradle9.3.1明确测试矩阵内。首个原生包必须保存gradlew --version/buildEnvironment结果并实际通过Debug/Release编译，不能先把这个组合标成原生兼容PASS。

技术基线0.8已通过T15整体确认，包含[验收与构建证据规范](technical/验收与构建证据规范.md)：名称/包名按T14固定，正式包排除测试Clock/夹具入口；性能使用真实正式签名非debuggable APK。SQLite发布包内置3.50.3，单原生连接及wal/2/1读回为小样必测约束；详细风险与版本证据见[依赖核查](依赖可行性核查-20261009.md)。

## 4. 验收

矩阵已确认API29/36、360/393dp、100%/200%字号的8种组合，覆盖手势/三键导航、键盘和TalkBack。标准性能AVD为API36、4核/4GiB、393dp、100%字号；release以100计划×3年历史测冷启动≤3秒、切月/详情≤1秒，具体数据生成及计时步骤见[技术文档§10.2](技术设计文档-计划打卡-Android-v1.md)。这是测试数据集，不是数量上限。

| 层级 | 验证 |
| --- | --- |
| 构建启动 | 安装、冷启动、原生插件、普通SQLite、备份/迁移排除配置 |
| 规则 | 三类计划、方向、打卡、补记、统计、时区；日历单摘要与逐项明细，跳过的两种分母不混用 |
| 存储 | 飞行模式、重复点击、重启、升级失败 |
| 交互 | Back、键盘、安全区、大字号、TalkBack |
| 范围 | 三入口，无延期能力入口与权限请求 |
| 独立产物 | 关闭 Metro、离线安装与重启 |

厂商设备、系统升级和长期性能需要真机补充；模拟器通过不代表发布检查全部通过。首版没有相机/推送/云端链路。

详细用例AT01–AT28及待确认状态见 [设计需求文档](设计需求文档-计划打卡-Android-v1.md)。记录应用版本、包类型、系统 API、尺寸/字号/导航、步骤、期望/实际、截图/日志；源码、静态、构建、模拟器、真机分开记录，未执行为 NOT_RUN。
