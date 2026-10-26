import 'react-native-gesture-handler';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { ActivityIndicator, Text, View } from 'react-native';
import { AppProvider } from '../src/state/AppProvider';

export default function RootLayout() {
  const [fonts,error]=useFonts({NotoSC400:require("../assets/fonts/generated/NotoSansSC-400.ttf"),NotoSC600:require("../assets/fonts/generated/NotoSansSC-600.ttf"),NotoSC700:require("../assets/fonts/generated/NotoSansSC-700.ttf"),Inter400:require("../assets/fonts/generated/Inter-400.ttf"),Inter600:require("../assets/fonts/generated/Inter-600.ttf"),Inter700:require("../assets/fonts/generated/Inter-700.ttf"),NotoSC:require("../assets/fonts/generated/NotoSansSC-400.ttf"),Inter:require("../assets/fonts/generated/Inter-400.ttf")});
  return (
    <SafeAreaProvider><StatusBar style="dark" />{error?<View style={{flex:1,justifyContent:'center',padding:24}}><Text>本机字体资源加载失败，请重新启动或安装完整应用。</Text></View>:fonts?<AppProvider><Stack screenOptions={{ headerShown: false, statusBarStyle: 'dark' }} /></AppProvider>:<View style={{flex:1,justifyContent:'center'}}><ActivityIndicator/></View>}</SafeAreaProvider>
  );
}
