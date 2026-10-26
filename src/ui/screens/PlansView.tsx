import React from 'react';
import {SpecScreen,type RenderOptions} from '../spec-renderer';
import {documentByTitle} from '../spec-documents';
export function PlansView(options:RenderOptions){return <SpecScreen document={documentByTitle('03-')} {...options}/>;}
