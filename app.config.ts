import type { ExpoConfig } from 'expo/config';

export default function config(): ExpoConfig {
const development = process.env.APP_VARIANT === 'development';
return {
  name: '计划打卡',
  slug: 'android-plan-checkin',
  version: '1.0.0',
  orientation: 'portrait',
  scheme: development ? 'plancheckin-dev' : 'plancheckin',
  userInterfaceStyle: 'light',
  updates: { enabled: false, checkAutomatically: 'NEVER' },
  android: {
    package: development ? 'com.xiang.plancheckin.dev' : 'com.xiang.plancheckin',
    versionCode: 1,
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
