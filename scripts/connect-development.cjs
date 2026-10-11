const {DeviceDriver}=require('./device-driver.cjs');
const api=process.argv[2]||'36',device=new DeviceDriver(api,'.cache/verification-bridge/connect');
device.identity();device.adb(['reverse','tcp:8081','tcp:8081']);
device.deepLink(process.argv[3]==='native'?'plancheckin-dev://native':'plancheckin-dev://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081');
console.log('Restored only the task Metro reverse and development launch URI; no business operation was submitted.');
