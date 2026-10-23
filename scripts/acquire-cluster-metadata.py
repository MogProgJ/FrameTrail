"""Bounded Open Images train metadata acquisition/catalogue; never downloads photographs."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import urllib.request
import uuid


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_sources(spec):
    if spec.get('schema') != 1 or spec.get('publisher_split') != 'train':
        raise ValueError('Expected the pinned publisher-train source specification')
    filenames = set()
    total = 0
    for entry in spec['files']:
        name = entry['filename']
        size = entry['http_content_length_observed']
        if (not name or Path(name).name != name or '/' in name or '\\' in name
                or name in filenames or type(size) is not int or size <= 0
                or not entry['url'].startswith('https://storage.googleapis.com/openimages/')):
            raise ValueError('Invalid metadata filename, URL or expected size')
        filenames.add(name)
        total += size
    cap = spec['suggested_metadata_download_cap_bytes']
    if type(cap) is not int or not 0 < total <= cap <= 4000000000:
        raise ValueError('Metadata exceeds the 4 GB stored-data budget')
    return total


def acquire(entry, directory, opener=urllib.request.urlopen):
    """Preserve completed files; resume only against an unchanged HTTP validator."""
    destination = directory / entry['filename']
    receipt = destination.with_name(destination.name + '.receipt.json')
    part = destination.with_name(destination.name + '.part')
    state_path = destination.with_name(destination.name + '.part.json')
    url, expected = entry['url'], entry['http_content_length_observed']
    if destination.exists():
        record = read_json(receipt)
        if (record['url'] != url or record['bytes'] != expected
                or destination.stat().st_size != expected
                or sha256(destination) != record['sha256']):
            raise ValueError(f'Existing metadata changed: {destination.name}')
        print(f'Reusing verified metadata: {destination.name}', flush=True)
        return record
    offset = part.stat().st_size if part.exists() else 0
    headers = {'Accept-Encoding': 'identity'}
    state = None
    if part.exists():
        state = read_json(state_path)
        if (state['url'] != url or state['bytes_expected'] != expected
                or not 0 <= offset <= expected):
            raise ValueError('Partial download identity/size mismatch; preserve it for diagnosis')
        if offset:
            if not state['validator']:
                raise ValueError('Partial download lacks a HTTP validator; cannot safely resume')
            headers.update(Range=f'bytes={offset}-', **{'If-Range': state['validator']})
    if offset < expected:
        request = urllib.request.Request(url, headers=headers)
        with opener(request, timeout=60) as response:
            if not response.geturl().startswith('https://storage.googleapis.com/openimages/'):
                raise ValueError('Unexpected metadata redirect')
            status = response.status
            etag = response.headers.get('ETag')
            modified = response.headers.get('Last-Modified')
            validator = etag if etag and not etag.startswith('W/') else modified
            if offset:
                if (status != 206 or validator != state['validator']
                        or response.headers.get('Content-Range') != f'bytes {offset}-{expected-1}/{expected}'):
                    raise ValueError('Server did not resume the same metadata object; partial file preserved')
            elif status != 200:
                raise ValueError('Expected a complete metadata HTTP response')
            if int(response.headers.get('Content-Length', '-1')) != expected - offset:
                raise ValueError('Publisher length changed; update sources after investigation')
            if not part.exists():
                save_json(state_path, {'url': url, 'bytes_expected': expected,
                                      'validator': validator, 'etag': etag, 'last_modified': modified})
            mode = 'ab' if part.exists() else 'xb'
            current, next_progress = offset, offset + 100000000
            with part.open(mode) as stream:
                while chunk := response.read(1024 * 1024):
                    if current + len(chunk) > expected:
                        raise ValueError('Metadata byte limit exceeded')
                    stream.write(chunk)
                    current += len(chunk)
                    if current >= next_progress:
                        print(f'{destination.name}: {current}/{expected} bytes', flush=True)
                        next_progress = current + 100000000
    if part.stat().st_size != expected:
        raise ValueError('Truncated metadata response; rerun to resume the preserved partial file')
    state = read_json(state_path)
    record = {'url': url, 'bytes': expected, 'sha256': sha256(part),
              'retrieved_at_utc': timestamp(), 'etag': state['etag'],
              'last_modified': state['last_modified'],
              'verification': 'HTTP object identity/length and local SHA256; no publisher checksum supplied'}
    # Publish without overwriting an existing completed file. Recover a stopped
    # publication using the full-size .part and its validator on the next run.
    save_json(receipt, record)
    os.link(part, destination)
    part.unlink()
    state_path.unlink()
    print(f'Acquired: {destination.name} SHA256={record["sha256"]}', flush=True)
    return record


def verify_classes(publisher_path, frozen_path, expected_digest, vocabulary):
    if sha256(frozen_path) != expected_digest:
        raise ValueError('Frozen normalized class-file hash differs from the prepared source specification')
    with Path(publisher_path).open(newline='', encoding='utf-8-sig') as stream:
        publisher = list(csv.DictReader(stream))
    with Path(frozen_path).open(newline='', encoding='utf-8-sig') as stream:
        frozen = list(csv.reader(stream))
    mids = [row[0] for row in frozen]
    official = [row['LabelName'] for row in publisher]
    if (len(mids) != 601 or len(official) != 601 or len(set(mids)) != 601
            or set(mids) != set(official)
            or {row[1] for row in frozen} != {item['name'] for item in vocabulary}):
        raise ValueError('Publisher IDs/frozen vocabulary differ; do not reorder the model head')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true', help='Explicitly acquire metadata and build the catalogue')
    args = parser.parse_args()
    root, inputs = args.root.resolve(strict=True), args.inputs.resolve(strict=True)
    spec_path = inputs / 'openimages-train-sources.json'
    spec = read_json(spec_path)
    total = validate_sources(spec)
    sys.path.insert(0, str(root / 'scripts'))
    import training_data as data
    frozen = inputs / 'classes.csv'
    if sha256(frozen) != spec['frozen_normalized_classes']['sha256']:
        raise ValueError('Transferred normalized classes file changed')
    scope_path = inputs / 'general-intake-pilot.json'
    scope = read_json(scope_path)
    known = {item['canonical_name'] for item in data.vocabulary()}
    if (scope.get('max_images') != 600 or len(scope['domains']) != 6
            or any(name not in known for names in scope['domains'].values() for name in names)):
        raise ValueError('Unexpected six-domain pilot policy')
    metadata, output = args.metadata.resolve(), args.output.resolve()
    for path in (metadata, output):
        if not path.is_relative_to(root / 'output'):
            raise ValueError('Derived data must remain inside this project output directory')
    report = {'schema': 1, 'status': 'preflight', 'metadata_bytes_expected': total,
              'stored_metadata_cap_bytes': spec['suggested_metadata_download_cap_bytes'],
              'publisher_split': 'train', 'photographs_downloaded': 0,
              'image_level_labels_indexed': False, 'approved_for_training': False,
              'source_spec_sha256': sha256(spec_path), 'scope_sha256': sha256(scope_path),
              'runner_sha256': sha256(__file__),
              'catalogue_source_sha256': sha256(root / 'scripts/training_data.py')}
    if not args.run:
        print(json.dumps(report, indent=2))
        return
    if output.exists():
        raise FileExistsError('Choose a new job-specific output; previous reports are preserved')
    output.mkdir(parents=True)
    metadata.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(metadata).free < 20 * 1024**3:
        raise ValueError('Need at least 20 GiB filesystem space for metadata, catalogue and temporary files')
    report.update(status='acquiring_metadata', started_at_utc=timestamp())
    save_json(output / 'preparation.json', report)
    try:
        records = []
        for entry in spec['files']:
            records.append(acquire(entry, metadata))
            report['files'] = records
            save_json(output / 'preparation.json', report)
        verify_classes(metadata / 'oidv7-class-descriptions-boxable.csv', frozen,
                       spec['frozen_normalized_classes']['sha256'], data.vocabulary())
        report['status'] = 'indexing'
        save_json(output / 'preparation.json', report)
        target = output / 'openimages-train.sqlite'
        print(f'Building publisher-train catalogue: {target}', flush=True)
        data.catalogue(metadata / 'oidv6-train-annotations-bbox.csv', frozen,
                       metadata / 'train-images-boxable-with-rotation.csv', target, 'train')
        with sqlite3.connect(f'file:{target.as_posix()}?mode=ro', uri=True) as db:
            inventory = data.inventory(db, scope)
        save_json(output / 'inventory.json', inventory)
        report.update(status='completed', finished_at_utc=timestamp(),
                      catalogue_sha256=sha256(target),
                      catalogue_images=inventory['catalogue_images'],
                      catalogue_boxes=inventory['catalogue_boxes'],
                      raw_labels=inventory['raw_labels'],
                      canonical_categories=inventory['canonical_categories'],
                      classes_with_boxes=sum(item['annotated_images'] > 0 for item in inventory['classes']))
    except BaseException as error:
        report.update(status='failed', error=str(error), finished_at_utc=timestamp())
        raise
    finally:
        save_json(output / 'preparation.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
