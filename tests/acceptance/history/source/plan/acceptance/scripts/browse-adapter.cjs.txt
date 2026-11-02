'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {NativeAdapter}=require('../../../tests/ui/native-adapter.cjs'),{decode}=require('../../../scripts/device-driver.cjs');
function report(xml){const tags=[...xml.matchAll(/<[^>]*resource-id="ui-review.chunk.(\d+)"[^>]*>/g)],chunks=[];for(const tag of tags){const raw=tag[0].match(/content-desc=(["'])(.*?)\1/)?.[2];if(raw!==undefined)chunks[Number(tag[1])]=decode(raw);}if(!chunks.length)return null;try{return JSON.parse(chunks.join(''));}catch{return null;}}
class BrowseAdapter extends NativeAdapter{
 async open(){const identity=await super.open();await this.device.clickVisible('native.ui-review');await this.device.waitSource(x=>x.includes('resource-id="ui-review.command"'));return identity;}
 async command(value){const element=await this.device.id('ui-review.command');await this.device.request(this.device.endpoint('element/'+element+'/value'),'POST',{text:JSON.stringify(value)+'\n'});}
 async observe(name,{save=true}={}){let before=report(await this.device.source()),result;await this.device.click('ui-review.capture');await this.device.waitSource(x=>{result=report(x);return result&&result.nonce!==before?.nonce;});assert.ok(!result.error,JSON.stringify(result));if(save){const capture=await this.capture(name);fs.writeFileSync(path.join(this.directory,name+'.json'),JSON.stringify(result));return {report:result,evidence:capture};}return {report:result};}
 async restart(context){await this.command({type:'restart'});await this.device.waitSource(x=>x.includes('viewport-bCoiJ'));if(context){await this.command({type:'configure',context});await this.device.waitSource(x=>x.includes('viewport-bCoiJ'));}return this.observe('restart-'+Date.now(),{save:false});}
 async perform(c){const response=c.mocks.find(m=>m.boundary.includes('record-response'))?.response.value;if(response)await this.command({type:'response',response});await this.device.clickVisible(c.operation.input.controlNodeId);if(c.operation.input.selection){const selection=c.operation.input.selection;await this.device.waitSource(x=>[...x.matchAll(/\btext="([^"]*)"/g)].some(m=>decode(m[1])===selection));await this.device.text(selection);}}
 async shutdown(){await this.command({type:'close'});await this.device.waitSource(x=>x.includes('resource-id="native.ui-review"'));await this.capture('browse-host-restored');}
}
module.exports={BrowseAdapter,report};
