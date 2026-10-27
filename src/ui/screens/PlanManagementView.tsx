import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
export function PlanManagementView({kind='manage',...options}:RenderOptions&{kind?:'manage'|'archive'|'delete'}){return <SpecScreen document={documentByTitle(kind==='archive'?'17-':kind==='delete'?'18-':'16-')} {...options}/>;}
