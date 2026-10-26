import {documentByTitle} from './spec-documents';
import type {Inputs} from './spec-types';
export interface PlanFormPresentation {editing:boolean;type:'fixed'|'weekly'|'one_time';name:string;description:string;zone:string;target:string;due:string}
export function planFormPresentation(value:PlanFormPresentation){const n=Number(value.target);const inputs:Inputs={'plan.name':value.name,'plan.description':value.description,'plan.timeZone':value.zone,'task.name':value.name,'task.description':value.description,'task.deadline':value.due,'weekly.targetDays':Number.isInteger(n)?n:0};return {document:documentByTitle(value.editing?'15-':value.type==='weekly'?'05-':value.type==='one_time'?'06-':'04-'),inputs};}
