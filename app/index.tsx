import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function Index() {
  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.title} accessibilityRole="header">计划打卡</Text>
      <LinearGradient colors={['#ffffff', '#e3e5e7', '#f8f9fa']} style={styles.surface}>
        <View style={styles.content}>
          <Text style={styles.heading}>开始记录每一天</Text>
          <Text style={styles.body}>把计划落实到行动，留下属于自己的进展。</Text>
        </View>
      </LinearGradient>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f1f2f3', padding: 24 },
  title: { fontSize: 30, fontWeight: '700', color: '#25282b', marginBottom: 28 },
  surface: { borderRadius: 6, borderWidth: 1, borderColor: '#fff', boxShadow: '0 6px 16px rgba(0,0,0,0.12)' },
  content: { padding: 20, gap: 12 },
  heading: { fontSize: 20, fontWeight: '600', color: '#25282b' },
  body: { fontSize: 15, color: '#575c61', lineHeight: 24 },
});
