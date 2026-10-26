import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
import type {SpecDocument} from '../spec-types';
export function RecordFormView({document,kind='ordinary',...options}:RenderOptions&{document?:SpecDocument;kind?:'ordinary'|'avoid'|'modify'|'backfill'|'complete'|'readonly'}){const prefix={ordinary:'07-',avoid:'08-',modify:'09-',backfill:'10-',complete:'21-',readonly:'22-'}[kind];return <SpecScreen document={document??documentByTitle(prefix)} {...options}/>;}
