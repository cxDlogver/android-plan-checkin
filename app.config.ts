import type { ExpoConfig } from 'expo/config';

export default function config(): ExpoConfig {
const development = process.env.APP_VARIANT === 'development';
const versionCode = Number(process.env.PLANCHECKIN_VERSION_CODE || '1');
const version = process.env.PLANCHECKIN_VERSION_NAME || '1.0.0';
if (!Number.isSafeInteger(versionCode) || versionCode < 1 || versionCode > 2100000000) throw new Error('PLANCHECKIN_VERSION_CODE must be a positive Android version code.');
if (!/^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$/.test(version)) throw new Error('PLANCHECKIN_VERSION_NAME must be a semantic version.');
return {
  name: '计划打卡',
  slug: 'android-plan-checkin',
  version,
  orientation: 'portrait',
  scheme: development ? 'plancheckin-dev' : 'plancheckin',
  userInterfaceStyle: 'light',
  updates: { enabled: false, checkAutomatically: 'NEVER' },
  android: {
    package: development ? 'com.xiang.plancheckin.dev' : 'com.xiang.plancheckin',
    versionCode,
    allowBackup: false,
    blockedPermissions: [
      'android.permission.POST_NOTIFICATIONS',
      'android.permission.ACCESS_COARSE_LOCATION',
      'android.permission.ACCESS_FINE_LOCATION',
      'android.permission.CAMERA',
      'android.permission.RECORD_AUDIO',
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.READ_MEDIA_VIDEO',
      'android.permission.READ_EXTERNAL_STORAGE',
      'android.permission.WRITE_EXTERNAL_STORAGE',
    ],
  },
  plugins: [
    'expo-router',
    ['expo-build-properties', { android: { minSdkVersion: 29, compileSdkVersion: 36, targetSdkVersion: 36 } }],
    './plugins/with-local-only.cjs',
    './plugins/with-release-signing.cjs',
    ...(development ? ['expo-dev-client'] : []),
  ],
};
}
