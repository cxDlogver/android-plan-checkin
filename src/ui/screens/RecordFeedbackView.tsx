import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
export function RecordFeedbackView({dateChanged=false,...options}:RenderOptions&{dateChanged?:boolean}){return <SpecScreen document={documentByTitle(dateChanged?'23-':'20-')} {...options}/>;}
