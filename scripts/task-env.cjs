const path = require('node:path');
const { spawnSync } = require('node:child_process');
const toolRoot = process.env.ANDROID_AI_TOOL_ROOT || 'D:/xiang/CX_application/1_Configuration_Files/Android-AI';
const nodeRoot = path.join(toolRoot, 'node-v24.21.0-win-x64');
const javaRoot = process.env.PLANCHECKIN_JAVA_HOME || 'D:/xiang/CX_application/1_Configuration_Files/JAVA/jdk-17.0.1';
const env = {
  ...process.env,
  JAVA_HOME: javaRoot,
  ANDROID_HOME: path.join(toolRoot, 'sdk'),
  ANDROID_SDK_ROOT: path.join(toolRoot, 'sdk'),
  ANDROID_USER_HOME: path.join(toolRoot, 'android-user'),
  ANDROID_AVD_HOME: path.join(toolRoot, 'avd'),
  APPIUM_HOME: path.join(toolRoot, 'appium-home'),
  ANDROID_AI_TOOL_ROOT: toolRoot,
  GRADLE_USER_HOME: path.resolve('.cache/gradle'),
  npm_config_cache: path.resolve('.cache/npm'),
  npm_config_registry: 'https://registry.npmjs.org/',
  CI: '1',
  EXPO_NO_TELEMETRY: '1',
  GIT_TERMINAL_PROMPT: '0',
  GCM_INTERACTIVE: 'never',
};
env.PATH = [nodeRoot, path.join(javaRoot, 'bin'), path.join(toolRoot, 'sdk/platform-tools'), path.join(toolRoot, 'sdk/emulator'), process.env.PATH].join(path.delimiter);
// 复用本机已启用的代理，仅影响本任务子进程，不修改系统设置。
if (!env.npm_config_https_proxy && !env.HTTPS_PROXY) {
  const enabled = spawnSync('reg', ['query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyEnable'], { encoding: 'utf8', windowsHide: true });
  const settings = spawnSync('reg', ['query', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings', '/v', 'ProxyServer'], { encoding: 'utf8', windowsHide: true });
  const proxy = settings.stdout?.match(/ProxyServer\s+REG_SZ\s+([^\r\n]+)/)?.[1]?.trim();
  if (/0x1/.test(enabled.stdout || '') && proxy && /^[\w.-]+:\d+$/.test(proxy)) {
    env.npm_config_https_proxy = `http://${proxy}`;
    env.npm_config_proxy = `http://${proxy}`;
  }
}
module.exports = { toolRoot, nodeRoot, javaRoot, env, node: path.join(nodeRoot, 'node.exe') };
