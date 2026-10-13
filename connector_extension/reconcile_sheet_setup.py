"""Operator-only read reconciliation of a previously journaled spreadsheet setup."""
import argparse
import json
from pathlib import Path
from .app import configuration, state_directory
from .catalog import CATALOG
from .common import EffectJournal
from .google import GoogleAPI, GoogleToken
from .sheet_creation import SheetResourceStore, SheetsSetup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--input-file', required=True, type=Path, help='Exact reviewed tool input JSON, not credentials.')
    parser.add_argument('--tool', required=True, choices=['extension_sheets_create', 'extension_sheets_add_tabs'])
    parser.add_argument('--spreadsheet', required=True, help='Operator-selected existing result link/ID.')
    parser.add_argument('--workflow-id', required=True)
    parser.add_argument('--version', type=int, required=True)
    args = parser.parse_args()
    try:
        if args.version < 1: raise ValueError()
        config = configuration(args.config); state = state_directory()
        if not config.get('sheet_creation_enabled') or not (state/'effects.sqlite3').is_file(): raise ValueError()
        connector = SheetsSetup(CATALOG[args.tool], GoogleAPI(GoogleToken(state/'google-token.json')),
            EffectJournal(state), SheetResourceStore(state), config.get('sheet_reads', []), config.get('sheet_writes', []))
        connector = connector.bind_workflow({'workflow_id':args.workflow_id,'version':args.version,
                                            'metadata':{'workspace_id':'local-workspace'}})
        result = connector.reconcile(json.loads(args.input_file.read_text()), args.spreadsheet)
    except Exception:
        parser.exit(1, 'Reconciliation failed; verify the original intent, marker and manifest. No provider write or repeat was made.\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
