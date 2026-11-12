import {describe,it,expect} from 'vitest';
import {communicationStatuses} from './communication-status';
describe('independent confirmed delivery statuses',()=>{
 it('never treats generated content as delivery',()=>{
  expect(communicationStatuses({report:{state:'completed',capability_id:'content.prepare',output:{summary:'Email sent'}}})).toEqual([]);
 });
 it('retains email confirmation when Calendar fails',()=>{
  const statuses=communicationStatuses({mail:{state:'completed',verified_receipt:true,capability_id:'tool.extension_mail_send',output:{message_id:'confirmed'}},calendar:{state:'failed',capability_id:'tool.extension_calendar_create'}});
  expect(statuses.map(s=>s.label)).toEqual(['Report emailed','Review needs attention']);
 });
 it('requires real identifiers and excludes cancelled events',()=>{
  expect(communicationStatuses({x:{state:'completed',verified_receipt:true,capability_id:'tool.extension_calendar_create',output:{status:'cancelled',event_id:'event'}}})[0]?.label).not.toBe('Review scheduled');
  expect(communicationStatuses({x:{state:'completed',verified_receipt:false,capability_id:'tool.extension_mail_send',output:{message_id:'untrusted'}}})[0]?.label).toBe('Email pending');
 });
});
