"""Operator report reconciliation uses actual marker/content read-back, never writes."""
import json

import pytest

from connector_extension import reconcile_sheet_setup as command
from connector_extension.tests import test_sheet_report as fixtures


@pytest.fixture
def report(tmp_path, monkeypatch):
    f = fixtures.ReportTests()
    f.setUp()
    try:
        f.http.fail_verification = True
        with pytest.raises(Exception):
            f.invoke(effect='run_original:report')
        f.http.fail_verification = False
        f.http.calls.clear()
        f.input_file = tmp_path / 'reviewed-inputs.json'
        f.input_file.write_text(json.dumps(f.inputs))
        monkeypatch.setattr(command, 'configuration', lambda _: {'sheet_creation_enabled': True})
        monkeypatch.setattr(command, 'state_directory', lambda: f.root)
        monkeypatch.setattr(command, 'GoogleToken', lambda _: None)
        monkeypatch.setattr(command, 'GoogleAPI', lambda _: f.api)
        f.args = ['reconcile', '--config', str(tmp_path / 'operator.json'),
                  '--input-file', str(f.input_file), '--tool', fixtures.TOOL,
                  '--spreadsheet', 'created_1', '--workflow-id', f.workflow['workflow_id'],
                  '--version', '1', '--workspace', 'local-workspace',
                  '--effect-id', 'run_original:report']
        yield f
    finally:
        f.tearDown()


def test_operator_command_verifies_exact_report_without_repeating_write(report, monkeypatch, capsys):
    f = report
    monkeypatch.setattr('sys.argv', f.args)
    command.main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['spreadsheet_id'] == 'created_1'
    assert receipt['written_rows'] == 3
    assert f.http.calls and all(c['method'] == 'GET' for c in f.http.calls)
    assert f.http.write_count == 1
    assert f.invoke(effect='run_original:report')['reused']


@pytest.mark.parametrize('mismatch', ['effect', 'workspace', 'inputs', 'missing_effect'])
def test_operator_command_rejects_mismatched_identity_or_manifest(report, monkeypatch, mismatch):
    f = report
    if mismatch == 'effect':
        f.args[-1] = 'run_unrelated:report'
    elif mismatch == 'workspace':
        f.args[f.args.index('--workspace') + 1] = 'another_customer'
    elif mismatch == 'missing_effect':
        f.args = f.args[:-2]
    else:
        f.inputs['tabs'][0]['rows'][0][1] = 999
        f.input_file.write_text(json.dumps(f.inputs))
    monkeypatch.setattr('sys.argv', f.args)
    with pytest.raises(SystemExit) as denied:
        command.main()
    assert denied.value.code == 1
    assert all(c['method'] == 'GET' for c in f.http.calls)
    assert f.http.write_count == 1
