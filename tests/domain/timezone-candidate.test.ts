import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validZone, date } from '../../src/domain/date';
import { DomainError } from '../../src/domain/model';
for (const [row,candidate,expected] of [['valid','Asia/Shanghai',true],['null',null,false],['invalid','Invalid/Zone',false]] as const) {
  test(`AC108/${row}: candidate must be an explicit valid IANA zone`,()=>{
    assert.equal(validZone(candidate as unknown as string),expected);
    if(expected)assert.equal(date('2026-10-09',candidate!).zoneName,candidate);
    else assert.throws(()=>date('2026-10-09',candidate as unknown as string),error=>error instanceof DomainError&&error.code==='VALIDATION_FAILED');
  });
}
