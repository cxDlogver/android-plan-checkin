# 验收记录与复现入口

本目录保留用例定义、合同、执行清单、历史实际结果和截图等证据。

可执行测试代码已统一迁到 [`tests/`](../../tests/README.md)。复现单个用例使用 `pnpm test:case <caseId>`，检查映射与依赖使用 `pnpm test:check`。

历史记录中的命令、脚本路径、断言和摘要记录的是原执行现场，保持原样。对应源码快照的当前位置见 [source-map.json](../../tests/acceptance/source-map.json)。源码快照是证据数据，独立复现的当前入口为 [`run-case.cjs`](../../tests/acceptance/run-case.cjs)。
