"""Explicit local attachment staging; never reads an arbitrary path from a model."""
import argparse
from pathlib import Path
from .common import ArtifactStore, MAX_ATTACHMENT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True, help='Operator-selected local attachment.')
    parser.add_argument('--workflow-id', required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--state-dir', type=Path)
    args = parser.parse_args()
    if args.version < 1: parser.error('--version must be positive')
    from .app import state_directory
    try:
        with args.file.open('rb') as handle: content = handle.read(MAX_ATTACHMENT + 1)
        store = ArtifactStore(state_directory(args.state_dir))
        identifier = store.put(['local-workspace', args.workflow_id, args.version], content)
    except Exception:
        parser.exit(1, 'Attachment staging failed. Choose an accessible file of at most five MiB.\n')
    print(identifier)

if __name__ == '__main__': main()
