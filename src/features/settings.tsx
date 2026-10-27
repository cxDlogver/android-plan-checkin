import * as Application from 'expo-application';
import {router} from 'expo-router';
import {settingsVersion} from '@verification/runtime';
import {useApp} from '../state/AppProvider';
import {SettingsView} from '../ui/screens/SettingsView';
import {walk} from '../ui/screens/TodayView';
import {documentByTitle} from '../ui/spec-documents';
export default function Settings(){const {snapshot,queries}=useApp(),native=settingsVersion(Application.nativeApplicationVersion,Application.nativeBuildVersion),settings=queries.settings(snapshot,native.version,native.build),back=walk(documentByTitle('19-').tree).find(n=>n.name==='返回'&&n.kind==='vector')!;return <SettingsView inputs={{'app.version':settings.nativeVersion+'（'+settings.nativeBuild+'）'}} actions={{[back.parentId!]:{testID:'settings.back',label:'返回',accessible:false,onPress:()=>router.back()}}}/>;}
