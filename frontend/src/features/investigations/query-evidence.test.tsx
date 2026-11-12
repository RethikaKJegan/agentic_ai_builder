import { render,screen } from '@testing-library/react';
import { describe,it,expect } from 'vitest';
import { QueryEvidence } from './QueryEvidence';

describe('Persisted query evidence',()=>{
  it('renders complete Subway aggregates and join limitations with the existing results layout',()=>{
    render(<QueryEvidence instance={{state:'completed',verified_receipt:true,output:{query_id:'subway_fixture_query',ontology_version:'subway_v4',scope:{workspace_id:'client-subway',owner_id:'subway-client'},
      columns:[{id:'average',label:'Average order value'}],rows:[{average:'25.51'}],coverage:{complete_scan:true,aggregate_complete:true,returned_rows:1,total_result_rows:1,has_more:false,matched_records:50},
      sources:[{read_at:'2026-11-11T10:00:00Z'}],join_checks:[{relationship_id:'purchase_approval',unmatched_reference_rows:2,missing_reference_rows:1}]}}}/>);
    expect(screen.getByText(/50 matching records/)).toBeVisible();
    expect(screen.getByRole('cell',{name:'25.51'})).toBeVisible();
    expect(screen.getByText(/2 unmatched and 1 missing references/)).toBeVisible();
  });
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
