import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
export function CalendarView(options:RenderOptions){return <SpecScreen document={documentByTitle('11-')} {...options}/>;}
