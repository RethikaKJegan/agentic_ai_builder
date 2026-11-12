import {describe,expect,it} from 'vitest';
import {subwayCardSize,workflowCardTitle} from './workflow-card-layout';
describe('Subway workflow card presentation',()=>{
 it('uses meaningful action names for long instructions without changing the input',()=>{
  const instructions='Prepare source-backed content. '+ 'Detailed instructions. '.repeat(80);
  expect(workflowCardTitle('prepare_reconciliation_report',instructions)).toBe('Prepare reconciliation report');
  expect(instructions).toContain('Detailed instructions.');
 });
 it('keeps short business titles and bounds opaque identifiers',()=>{
  expect(workflowCardTitle('a','Check invoice amounts')).toBe('Check invoice amounts');
  expect(workflowCardTitle('x'.repeat(180),'Long instructions '.repeat(80)).length).toBeLessThanOrEqual(90);
  expect(subwayCardSize).toEqual({width:280,height:168});
 });
});
