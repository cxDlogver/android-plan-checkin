import { randomUUID } from 'node:crypto';
export function routeContext(instant=new Date()){
 const today=instant.toISOString().slice(0,10),day=(offset:number)=>new Date(Date.parse(today+'T00:00:00Z')+offset*86400000).toISOString().slice(0,10);
 return {identity:randomUUID(),today,previousDate:day(-2),deadline:day(1),time:instant.toISOString().slice(11,16),zone:'Asia/Shanghai',names:{fixed:'清晨阅读练习',weekly:'每周户外活动',avoid:'减少含糖饮料',task:'准备学习资料',recorded:'晚间舒展'},note:'本次脚本输入的备注',description:'以适合自己的节奏逐步完成。',targetDays:4,completedDays:2};
}
