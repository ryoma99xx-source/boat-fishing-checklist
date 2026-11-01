import test from 'node:test';
import assert from 'node:assert/strict';
import {getJstSelection} from '../clock.js';

test('the access date changes at Japanese midnight rather than UTC midnight',()=>{
 assert.deepEqual(getJstSelection(Date.parse('2026-10-26T14:59:59Z')),{date:'2026-10-26',slot:46});
 assert.deepEqual(getJstSelection(Date.parse('2026-10-26T15:00:00Z')),{date:'2026-10-27',slot:0});
 assert.deepEqual(getJstSelection(Date.parse('2026-10-26T15:30:00Z')),{date:'2026-10-27',slot:1});
});
test('Japanese dates handle year boundaries and the historical case without a fixed default',()=>{
 assert.deepEqual(getJstSelection(Date.parse('2026-12-31T15:10:00Z')),{date:'2027-01-01',slot:0});
 assert.deepEqual(getJstSelection(Date.parse('2026-10-23T23:30:00Z')),{date:'2026-10-24',slot:17});
});
