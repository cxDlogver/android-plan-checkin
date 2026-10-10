// 仅对本项目专用AVD的系统设置做控制链路小样，不测试计划打卡功能。
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const api = process.argv[2] || '36';
if (!['29','36'].includes(api)) throw new Error('API必须为29或36');
const root = process.env.ANDROID_AI_TOOL_ROOT || 'D:/xiang/CX_application/1_Configuration_Files/Android-AI';
const address = 'http://127.0.0.1:4723';
const serial = api === '29' ? 'emulator-5560' : 'emulator-5562';
const steps = [];
let sessionId;
async function request(endpoint, method='GET', body) {
  const response = await fetch(address+endpoint, {method, headers:{'content-type':'application/json'}, ...(body ? {body:JSON.stringify(body)} : {}), signal:AbortSignal.timeout(180000)});
  const result = await response.json();
  if (!response.ok || result.value?.error) throw new Error(`${method} ${endpoint}: ${result.value?.message || response.status}`);
  return result;
}
async function screenshot(name) {
  const result = await request(`/session/${sessionId}/screenshot`);
  const bytes = Buffer.from(result.value,'base64');
  assert.equal(bytes.subarray(1,4).toString(),'PNG');
  const target = path.join(root,'logs',`automation-api${api}-${name}.png`);
  fs.writeFileSync(target,bytes);
  return target;
}
async function waitSource(pattern) {
  let result;
  for(let attempt=0;attempt<20;attempt++) {
    result = await request(`/session/${sessionId}/source`);
    if(pattern.test(result.value))return result;
    await new Promise(resolve=>setTimeout(resolve,500));
  }
  fs.writeFileSync(path.join(root,'logs',`automation-api${api}-unexpected.xml`),result.value);
  await screenshot('unexpected');
  throw new Error(`目标页面未出现：${pattern}`);
}
async function main() {
  const avd = execFileSync(path.join(root,'sdk','platform-tools','adb.exe'),['-s',serial,'emu','avd','name'],{encoding:'utf8',timeout:10000});
  assert.ok(avd.split(/\r?\n/).map(line=>line.trim()).includes(`plancheckin_api${api}`),'只能验证本项目专用AVD');
  let health;
  for(let attempt=0;attempt<60;attempt++) {
    try { health = await request('/status'); if(health.value.ready)break; } catch(error) { if(attempt===59)throw error; }
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  assert.equal(health.value.ready,true);
  steps.push({step:'appium_health',status:'PASS'});
  const session = await request('/session','POST',{capabilities:{alwaysMatch:{platformName:'Android','appium:automationName':'UiAutomator2','appium:udid':serial,'appium:platformVersion':api==='29'?'10':'16','appium:appPackage':'com.android.settings','appium:appActivity':'.Settings','appium:noReset':true,'appium:forceAppLaunch':true,'appium:shouldTerminateApp':true,'appium:newCommandTimeout':180,'appium:uiautomator2ServerInstallTimeout':120000,'appium:uiautomator2ServerLaunchTimeout':120000},firstMatch:[{}]}});
  sessionId = session.value.sessionId;
  assert.ok(sessionId);
  steps.push({step:'native_session',status:'PASS',serial});
  await request(`/session/${sessionId}/execute/sync`,'POST',{script:'mobile: startActivity',args:[{action:'android.settings.SETTINGS',wait:true,stop:true,flags:'0x10008000'}]});
  const source = await waitSource(/package="com.android.settings"/);
  fs.writeFileSync(path.join(root,'logs',`automation-api${api}-settings.xml`),source.value);
  assert.ok(source.value.includes('com.android.settings'));
  steps.push({step:'settings_hierarchy',status:'PASS'});
  const item = await request(`/session/${sessionId}/element`,'POST',{using:'-android uiautomator',value:'new UiSelector().text("Display")'});
  const elementId = item.value['element-6066-11e4-a52e-4f735466cecf'];
  assert.ok(elementId);
  await request(`/session/${sessionId}/element/${elementId}/click`,'POST',{});
  const display = await waitSource(/Brightness|Dark theme|Font size|Display size/);
  fs.writeFileSync(path.join(root,'logs',`automation-api${api}-display.xml`),display.value);
  assert.ok(/Brightness|Dark theme|Font size|Display size/.test(display.value));
  steps.push({step:'element_click_and_display_assertion',status:'PASS',screenshot:await screenshot('display')});
  await request(`/session/${sessionId}/appium/device/press_keycode`,'POST',{keycode:4});
  const afterBack = await waitSource(/Network &amp; internet|Network & internet/);
  assert.ok(afterBack.value.includes('Network &amp; internet') || afterBack.value.includes('Network & internet'));
  steps.push({step:'android_back',status:'PASS',screenshot:await screenshot('settings')});
  await request(`/session/${sessionId}/execute/sync`,'POST',{script:'mobile: startActivity',args:[{action:'android.settings.DEVICE_INFO_SETTINGS',wait:true}]});
  await waitSource(/text="Device name"/);
  const name = await request(`/session/${sessionId}/element`,'POST',{using:'-android uiautomator',value:'new UiSelector().text("Device name")'});
  const nameId = name.value['element-6066-11e4-a52e-4f735466cecf'];
  await request(`/session/${sessionId}/element/${nameId}/click`,'POST',{});
  await waitSource(/class="android.widget.EditText"/);
  const input = await request(`/session/${sessionId}/element`,'POST',{using:'class name',value:'android.widget.EditText'});
  const inputId = input.value['element-6066-11e4-a52e-4f735466cecf'];
  const originalName = (await request(`/session/${sessionId}/element/${inputId}/text`)).value;
  await request(`/session/${sessionId}/element/${inputId}/clear`,'POST',{});
  await request(`/session/${sessionId}/element/${inputId}/value`,'POST',{text:'Android AI smoke test'});
  const entered = await request(`/session/${sessionId}/element/${inputId}/text`);
  assert.equal(entered.value,'Android AI smoke test');
  steps.push({step:'text_input_and_readback',status:'PASS',screenshot:await screenshot('input')});
  const cancel = await request(`/session/${sessionId}/element`,'POST',{using:'id',value:'android:id/button2'});
  await request(`/session/${sessionId}/element/${cancel.value['element-6066-11e4-a52e-4f735466cecf']}/click`,'POST',{});
  const restored = await waitSource(/^(?![\s\S]*class="android.widget.EditText")[\s\S]*text="Device name"/);
  assert.ok(restored.value.includes(originalName));
  assert.ok(!restored.value.includes('Android AI smoke test'));
  steps.push({step:'cancel_input_without_setting_change',status:'PASS'});
}
main().catch(error=>{steps.push({step:'automation_error',status:'FAIL',message:error.message});process.exitCode=1;}).finally(async()=>{
  if(sessionId)try{await request(`/session/${sessionId}`,'DELETE');}catch(error){steps.push({step:'session_cleanup',status:'FAIL',message:error.message});process.exitCode=1;}
  const report={checkedAt:new Date().toISOString(),scope:'dedicated_avd_system_settings_only',api:Number(api),serial,steps,verification:{controlChain:steps.some(step=>step.status==='FAIL')?'FAIL':'PASS',planCheckinAcceptance:'NOT_RUN'}};
  fs.writeFileSync(path.join(root,'logs',`automation-api${api}.json`),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
});
