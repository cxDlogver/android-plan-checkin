# Test Case 复现

本目录仅保留与 `plan` 当前验收相关的测试、断言、设备驱动及必要源码证据。用例定义以 `plan/acceptance/test-cases.json` 为准，135 个 Test Case 与脚本的对应关系见 [cases.json](acceptance/cases.json)。

| 位置 | 内容 |
| --- | --- |
| `acceptance/run-case.cjs` | 按用例、轮次或完整顺序复现的入口 |
| `acceptance/` | 原生页面、响应式矩阵、视觉和回归夹具 |
| `ui/` | 独立 UI 断言、证据契约与原生适配器 |
| `support/` | 设备驱动、测试环境、隐藏子进程窗口的钩子 |
| `acceptance/history/` | 旧结果绑定的原始源码快照，作为不可修改的 `.txt` 证据保存 |

在项目根目录加载 Node 24 环境：

```powershell
. .\scripts\android-ai\Use-AndroidAI.ps1
```

检查脚本与用例映射、编译依赖、205 次主访问的 Node 行为和上下文入口：

```powershell
pnpm test:check
pnpm test:case --list
```

复现指定 Test Case；重复出现在原验收路线中的用例会复现它的全部必要访问：

```powershell
pnpm test:case TC-T051
pnpm test:case TC-G-EVIDENCE
```

原生用例需要已安装开发应用、API36 专用模拟器、Metro `8081` 和 Appium `4723`。可用测试环境脚本启动或复用服务：

```powershell
node tests/acceptance/start-services.cjs
```

按原规划顺序复现一轮或全部访问：

```powershell
pnpm test:case --round R01
pnpm test:case --all
```

复现结果写入 `.artifacts/acceptance/reproductions/<本次目录>/`，每次访问保存初态、实际操作、断言及相应证据，`progress.json` 保存断点。中断或修复环境问题后：

```powershell
pnpm test:case --resume .artifacts/acceptance/reproductions/<本次目录>
```

恢复会校验代码与已保存结果的摘要，仅跳过有效的已通过前缀；失败记录保留。代码发生变化时创建新复现记录，避免继续使用旧结果。原生复现会实际操作隔离开发宿主；`TC-G-SCOPE` 按其定义审查已记录主访问的调用边界。

这是独立复现入口，输出不覆盖 `plan` 中已完成验收的合同、状态、实际命令和历史结果。整理目录不会产生新的产品验收通过结论。原始规划中的旧脚本路径可通过 [source-map.json](acceptance/source-map.json) 找到对应的原始字节与摘要。
