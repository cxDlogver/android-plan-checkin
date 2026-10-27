import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
import type {SpecDocument} from '../spec-types';
export function PlanDetailView({kind='fixed',document,...options}:RenderOptions&{kind?:'fixed'|'weekly'|'one_time';document?:SpecDocument}){return <SpecScreen document={document??documentByTitle(kind==='weekly'?'13-':kind==='one_time'?'14-':'12-')} {...options}/>;}
