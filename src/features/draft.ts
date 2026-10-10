import { useRef, useState } from 'react';
import { useNavigation } from 'expo-router';
// Expo 57 embeds React Navigation; use its matching native-stack removal context.
import { usePreventRemove } from 'expo-router/build/react-navigation/core/usePreventRemove';
import { confirm } from '../ui/metal';
export function useDraftGuard(dirty:boolean,busy:boolean){
  const navigation=useNavigation(),approved=useRef(false),dialog=useRef(false),[allow,setAllow]=useState(false);
  usePreventRemove(!allow&&(dirty||busy),({data})=>{
    if(approved.current){navigation.dispatch(data.action);return;}
    if(busy||dialog.current)return;
    dialog.current=true;
    void confirm('放弃未保存内容？','返回会丢弃本页草稿，已保存的数据不会改变。').then(yes=>{
      dialog.current=false;
      if(yes){approved.current=true;setAllow(true);navigation.dispatch(data.action);}
    });
  });
  return ()=>{approved.current=true;setAllow(true);};
}
