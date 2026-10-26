import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
import type {SpecDocument} from '../spec-types';
export function PlanFormView({kind='fixed',editing=false,document,...options}:RenderOptions&{kind?:'fixed'|'weekly'|'one_time';editing?:boolean;document?:SpecDocument}){return <SpecScreen document={document??documentByTitle(editing?'15-':kind==='weekly'?'05-':kind==='one_time'?'06-':'04-')} {...options}/>;}
