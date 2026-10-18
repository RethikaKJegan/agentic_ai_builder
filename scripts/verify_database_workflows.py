"""Phase 5 regressions against disposable PostgreSQL/MongoDB; no cloud calls."""
from verify_database_crud import main

if __name__ == '__main__':
    raise SystemExit(main([
        'test_database_workflows', 'test_data_operations', 'test_data_selection',
        'test_data_queries', 'test_data_graph_v2', 'test_data_relationships',
        'test_data_sources', 'test_data_query_jobs', 'test_data_query_pushdown',
        'test_data_query_federation', 'test_runtime', 'test_dynamic_delegation',
        'test_registry', 'test_planner', 'test_planner_provider_errors',
        'test_live_providers', 'test_google_tools', 'test_google_connections',
        'test_sheet_records',
    ], '.local/phase5-workflow'))
