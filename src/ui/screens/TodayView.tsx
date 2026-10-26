import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
import {resolveText} from '../bindings';
import type {SpecDocument,SpecNode,Inputs,NodeAction} from '../spec-types';
export const walk=(n:SpecNode):SpecNode[]=>[n,...n.children.flatMap(walk)];
export function byName(document:SpecDocument,name:string):SpecNode{const n=walk(document.tree).find(n=>n.name===name);if(!n)throw new Error('缺少节点：'+name);return n;}
export function actionsByName(document:SpecDocument,handlers:Readonly<Record<string,NodeAction>>):Record<string,NodeAction>{return Object.fromEntries(walk(document.tree).flatMap(n=>handlers[n.name]?[[n.id,handlers[n.name]!]]:[]));}
export function materialize(node:SpecNode,key:string,inputs:Inputs,parentId:string|null=node.parentId):SpecNode{const id=node.id+'@'+key;return {...node,id,parentId,content:node.content?.type==='text'?{...node.content,binding:undefined,value:resolveText(node.content,inputs)}:node.content,sizing:{...node.sizing,width:node.sizing.width.binding?{...node.sizing.width,binding:undefined,value:Number(inputs[node.sizing.width.binding.path])}:node.sizing.width},children:node.children.map(c=>materialize(c,key,inputs,id))};}
export function literal(node:SpecNode,value:string):SpecNode{return {...node,content:{...node.content!,value,binding:undefined}};}
export function TodayView({empty=false,document,...options}:RenderOptions&{empty?:boolean;document?:SpecDocument}){return <SpecScreen document={document??documentByTitle(empty?'01-':'02-')} {...options}/>;}
