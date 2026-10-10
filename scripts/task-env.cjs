const path = require('node:path');
const toolRoot = 'D:/xiang/CX_application/1_Configuration_Files/Android-AI';
const nodeRoot = path.join(toolRoot, 'node-v24.21.0-win-x64');
const javaRoot = 'D:/xiang/CX_application/1_Configuration_Files/JAVA/jdk-17.0.1';
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
module.exports = { toolRoot, nodeRoot, javaRoot, env, node: path.join(nodeRoot, 'node.exe') };
