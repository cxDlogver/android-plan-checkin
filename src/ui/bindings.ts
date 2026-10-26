import type {Binding,Content,Dimension,Inputs} from './spec-types';
export function inputValue(inputs:Inputs,path:string):string|number {const value=inputs[path];if(value===undefined||value===null)throw new Error('缺少展示输入：'+path);return value;}
export function formatInput(value:string|number,definition:{type:string;format?:string}):string {
 const {type,format}=definition;
 if(type==='string'){if(typeof value!=='string')throw new Error('文本输入类型错误');return value;}
 if(type==='number'||type==='integer'){if(typeof value!=='number'||!Number.isFinite(value)||(type==='integer'&&!Number.isInteger(value)))throw new Error('数值输入类型错误');return format==='0%'?Math.round(value*100)+'%':String(value);}
 if(typeof value!=='string')throw new Error('日期输入类型错误');
 if(type==='time'){if(!/^\d{2}:\d{2}$/.test(value)||Number(value.slice(0,2))>23||Number(value.slice(3))>59)throw new Error('时间输入错误');return value;}
 if(type==='datetime'){const d=new Date(value);if(!Number.isFinite(+d))throw new Error('无效日期时间');if(format!=='M月d日 HH:mm')throw new Error('未支持日期时间格式：'+format);return (d.getUTCMonth()+1)+'月'+d.getUTCDate()+'日 '+d.toISOString().slice(11,16);}
 if(type==='date') {if(!/^\d{4}-\d{2}-\d{2}$/.test(value))throw new Error('日期输入错误');const d=new Date(value+'T00:00:00Z');if(!Number.isFinite(+d)||d.toISOString().slice(0,10)!==value)throw new Error('无效日期');const month=d.getUTCMonth()+1,day=d.getUTCDate();switch(format){case 'M月d日':return month+'月'+day+'日';case 'M月d日 EEEE':return month+'月'+day+'日 '+['星期日','星期一','星期二','星期三','星期四','星期五','星期六'][d.getUTCDay()];case 'yyyy年M月d日':return d.getUTCFullYear()+'年'+month+'月'+day+'日';case 'yyyy年M月':return d.getUTCFullYear()+'年'+month+'月';case 'd':return String(day);case 'yyyy-MM-dd':case undefined:return value;default:throw new Error('未支持日期格式：'+format);}}
 throw new Error('未支持展示类型：'+type);
}
export function resolveBinding(binding:Binding,inputs:Inputs):string{return binding.template.replace(/\{\{([^}]+)\}\}/g,(_,key:string)=>{const d=binding.parameters[key];if(!d)throw new Error('未声明绑定参数：'+key);return formatInput(inputValue(inputs,key),d);});}
export function resolveText(content:Content,inputs:Inputs):string{if(content.binding)return resolveBinding(content.binding,inputs);if(typeof content.value!=='string')throw new Error('文本缺少固定值或绑定');return content.value;}
export function resolvePercent(dimension:Dimension,inputs:Inputs):number{const v=dimension.binding?inputValue(inputs,dimension.binding.path):dimension.value;if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)throw new Error('比例必须在0至1之间');return v;}
