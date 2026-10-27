import {Tabs} from 'expo-router';
import {View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import type {ComponentProps} from 'react';
type BottomTabBarProps=Parameters<Exclude<ComponentProps<typeof Tabs>['tabBar'],undefined>>[0];
import {useApp} from '../../src/state/AppProvider';
import {documentByTitle} from '../../src/ui/spec-documents';
import {SpecFragment} from '../../src/ui/spec-renderer';
import type {SpecNode,NodeAction} from '../../src/ui/spec-types';
const flatten=(n:SpecNode):SpecNode[]=>[n,...n.children.flatMap(flatten)];
export function Navigation({state,navigation,descriptors}:BottomTabBarProps){const {clearPins}=useApp(),insets=useSafeAreaInsets();const active=state.routes[state.index]!.name;const doc=documentByTitle(active==='today'?'02-':active==='calendar'?'11-':'03-');const nav=flatten(doc.tree).find(n=>n.name==='三入口导航')!;const actions:Record<string,NodeAction>={};for(const child of nav.children){const name=child.name.startsWith('今日')?'today':child.name.startsWith('日历')?'calendar':'plans',route=state.routes.find(r=>r.name===name)!;actions[child.id]={testID:'tab.'+name,label:descriptors[route.key]?.options.title??name,selected:name===active,onPress:()=>{const event=navigation.emit({type:'tabPress',target:route.key,canPreventDefault:true});if(!event.defaultPrevented){clearPins();navigation.navigate(route.name);}}};}return <View style={{backgroundColor:'#E8ECF0',paddingBottom:insets.bottom,alignItems:'center'}}><View style={{width:'100%',maxWidth:480}}><SpecFragment node={nav} inputs={{}} actions={actions}/></View></View>;}
export default function TabLayout(){return <Tabs tabBar={props=><Navigation {...props}/>} screenOptions={{headerShown:false}}>{(['today','calendar','plans'] as const).map(name=><Tabs.Screen key={name} name={name} options={{title:{today:'今日',calendar:'日历',plans:'计划'}[name]}}/>)}</Tabs>;}
