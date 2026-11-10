import { render,screen } from '@testing-library/react';
import { describe,it,expect } from 'vitest';
import { QueryEvidence } from './QueryEvidence';

describe('Persisted query evidence',()=>{
  it('shows coverage separately from displayed rows',()=>{
    render(<QueryEvidence instance={{state:'completed',verified_receipt:true,output:{query_id:'dqj_actual',coverage:{complete_scan:true,aggregate_complete:false,returned_rows:1,total_result_rows:800,has_more:true},result:{matched_rows:800,executed_at:'2026-11-09T12:00:00Z',warnings:['Sources were read at different times.'],columns:[{key:'hours',label:'Operating hours'}],rows:[{hours:42}]}}}}/>);
    expect(screen.getByText(/800 matching records. Showing 1 of 800/)).toBeVisible();
    expect(screen.getByText(/display limit does not change calculated totals/)).toBeVisible();
    expect(screen.getByRole('cell',{name:'42'})).toBeVisible();
    expect(screen.getByText('Sources were read at different times.')).toBeVisible();
  });
  it('shows persisted progress without claiming success',()=>{
    render(<QueryEvidence instance={{state:'waiting_for_query',query_job:{progress:{stage:'Reading source'}}}}/>);
    expect(screen.getByRole('status')).toHaveTextContent('Reading source');
    expect(screen.queryByText('Verified query results')).toBeNull();
  });
  it('never presents an unverified result as verified',()=>{
    render(<QueryEvidence instance={{state:'failed',output:{query_id:'invented'}}}/>);
    expect(screen.queryByRole('region')).toBeNull();
  });
});
