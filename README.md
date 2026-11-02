# 计划打卡 Android

React Native / Expo 安卓应用，使用本机 SQLite 保存数据。

## 启动

完整的首次安装、日常运行、重新构建、故障排查与关闭步骤见 [项目启动文档](项目启动.md)。打包 APK、使用历史签名并保留数据覆盖正式版，见文档第 5 节。

在项目根目录打开 PowerShell：

```powershell
. .\scripts\android-ai\Use-AndroidAI.ps1
.\scripts\android-ai\Start-AndroidAIEmulator.ps1 -Api 36 -Visible
.\scripts\android-ai\Wait-AndroidAIReady.ps1 -Api 36
$env:APP_VARIANT = 'development'
pnpm start --host localhost --port 8081
```

已有运行中的模拟器时，省略启动模拟器的命令。模拟器和 Metro 就绪后，在 Metro 终端按 `a` 打开应用。

首次安装依赖：

```powershell
pnpm install --frozen-lockfile
```

未安装开发包或修改原生配置后，在已加载环境的项目终端执行：

```powershell
$env:APP_VARIANT = 'development'
pnpm exec expo prebuild --platform android --no-install --no-clean
pnpm exec expo run:android --device emulator-5562 --variant debug --no-bundler
pnpm start --host localhost --port 8081
```

环境使用 Node 24、pnpm 10.28.2、JDK 17。`scripts/android-ai/` 保留环境加载、模拟器启动、就绪检查及正式 APK 打包脚本。`resource/` 历史资料及此前迁出的非启动资料已删除。

打包正式 APK，自动复用固定签名，成功后版本号加 1：

```powershell
.\scripts\android-ai\Build-ReleaseApk.ps1
```

首版为 `1.0.0（versionCode 1）`，后续默认 `1.0.1（2）`、`1.0.2（3）`。固定产物为 `.artifacts/apk/release/plancheckin.apk`，每次成功覆盖；版本与固定路径记录在 [发布配置](config/release.json)。安装和数据保留步骤见 [项目启动文档](项目启动.md)第 5 节。

## Test Case 复现

所有可执行测试集中在 `tests/`，仅保留与当前 `plan` 验收相关的脚本。

```powershell
pnpm test:check
pnpm test:case --list
pnpm test:case TC-T051
```

完整运行、轮次和断点恢复命令见 [测试说明](tests/README.md)。
