"""Private, local archive extraction and aggregate-only BSON schema analysis."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import struct
import tarfile

from bson import BSON, ObjectId

EXCLUDE = {'tokens', 'clientsecrets', 'users', 'apilogs', 'auditlogs', 'mails', 'backuplogs'}


def typename(value):
    from datetime import datetime
    from bson.decimal128 import Decimal128
    if value is None: return 'null'
    if isinstance(value, bool): return 'boolean'
    if isinstance(value, ObjectId): return 'ObjectId'
    if isinstance(value, datetime): return 'datetime'
    if isinstance(value, Decimal128): return 'decimal'
    if isinstance(value, int): return 'integer'
    if isinstance(value, float): return 'number'
    if isinstance(value, str): return 'string'
    if isinstance(value, list): return 'array'
    if isinstance(value, dict): return 'object'
    return type(value).__name__


def records(path):
    with Path(path).open('rb') as handle:
        while True:
            head = handle.read(4)
            if not head: return
            if len(head) != 4: raise ValueError('Truncated BSON header')
            size = struct.unpack('<i', head)[0]
            if not 5 <= size <= 16 * 1024 * 1024: raise ValueError('Invalid BSON size')
            body = handle.read(size - 4)
            if len(body) != size - 4: raise ValueError('Truncated BSON record')
            yield head + body


def analyze(archive, directory, limit=200):
    archive, directory = Path(archive).resolve(), Path(directory).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    extracted = directory / 'extracted'; extracted.mkdir(mode=0o700)
    digest = hashlib.sha256()
    with archive.open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''): digest.update(block)
    members = []
    with tarfile.open(archive, 'r|gz') as source:
        for item in source:
            path = PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or not (item.isfile() or item.isdir()):
                raise ValueError('Archive contains an unsafe member')
            if item.isdir(): continue
            if not (item.name.endswith('.bson') or item.name.endswith('.metadata.json')):
                raise ValueError('Unexpected dump file type')
            target = extracted.joinpath(*path.parts)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            member_hash = hashlib.sha256()
            with source.extractfile(item) as data, target.open('xb') as output:
                os.chmod(target, 0o600)
                for block in iter(lambda: data.read(4 * 1024 * 1024), b''):
                    output.write(block); member_hash.update(block)
            if target.stat().st_size != item.size: raise ValueError('Extraction size mismatch')
            members.append(dict(name=item.name, bytes=item.size, sha256=member_hash.hexdigest()))
    profiles = []
    for path in sorted(extracted.rglob('*.bson')):
        name = path.name[:-5]
        metadata_path = path.with_name(name + '.metadata.json')
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        if name in EXCLUDE:
            profiles.append(dict(collection=name, database=path.parent.name, bytes=path.stat().st_size,
                excluded_from_business_access=True, reason='Authentication, operational logging or raw email content',
                metadata=metadata, fields=[], sampled_records=0))
            continue
        count = 0; sampled = 0; fields = defaultdict(Counter); present = Counter(); array_lengths = defaultdict(list)
        def walk(document, prefix='', depth=0):
            if depth > 6: return
            for key, value in document.items():
                field = prefix + str(key)
                fields[field][typename(value)] += 1
                present[field] += 1
                if isinstance(value, dict): walk(value, field + '.', depth + 1)
                elif isinstance(value, list):
                    array_lengths[field].append(len(value))
                    for item in value[:5]:
                        fields[field + '[]'][typename(item)] += 1
                        if isinstance(item, dict): walk(item, field + '[].', depth + 1)
        for raw in records(path):
            count += 1
            if sampled < limit:
                walk(BSON(raw).decode()); sampled += 1
        profiles.append(dict(collection=name, database=path.parent.name, bytes=path.stat().st_size,
            excluded_from_business_access=False, record_count=count, sampled_records=sampled,
            sampling='first N records in immutable dump order, not random', metadata=metadata,
            fields=[dict(path=k, types=dict(v), occurrences=present[k],
                **({'sampled_array_length_min':min(array_lengths[k]),'sampled_array_length_max':max(array_lengths[k])} if k in array_lengths else {})) for k,v in sorted(fields.items())]))
    report = dict(archive=archive.name, archive_sha256=digest.hexdigest(),
        members=members, collection_count=len(profiles), sample_limit=limit, collections=profiles,
        company_source_writes=0, external_model_calls=0)
    (directory / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(archive=archive.name, sha256=report['archive_sha256'], collections=len(profiles),
        business_collections=sum(not p['excluded_from_business_access'] for p in profiles),
        extracted_bytes=sum(m['bytes'] for m in members))), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    analyze(args.archive, args.directory)
