"""Versioned metadata-only intake selection. Never downloads or approves images."""
import argparse
from collections import Counter
import hashlib
import heapq
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

ALGORITHM = 'anchor-round-robin-v2'
ELIGIBLE_SQL = '''SELECT DISTINCT i.id FROM images i JOIN boxes b ON b.image_id=i.id
 JOIN classes c ON c.raw_id=b.raw_id WHERE c.canonical_id=?
 AND i.rotation IN ('0','0.0') AND i.license IN
 ('https://creativecommons.org/licenses/by/2.0/','http://creativecommons.org/licenses/by/2.0/')
 AND NOT EXISTS(SELECT 1 FROM boxes q WHERE q.image_id=i.id
                AND (q.group_of!=0 OR q.depiction!=0))'''


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def anchors(policy, canonical_names):
    for key, maximum in [('max_images', 600), ('images_per_category', 12),
                         ('max_download_bytes', 1000000000)]:
        if type(policy.get(key)) is not int or not 0 < policy[key] <= maximum:
            raise ValueError('Invalid pilot budget: ' + key)
    domains = policy.get('domains')
    if (policy.get('schema') != 1 or type(policy.get('seed')) is not int
            or not isinstance(domains, dict) or not domains
            or any(not domain or not isinstance(names, list) or not names
                   for domain, names in domains.items())):
        raise ValueError('Invalid pilot policy')
    ordered = [(domain, names[position])
               for position in range(max(map(len, domains.values())))
               for domain, names in domains.items() if position < len(names)]
    names = [name for _, name in ordered]
    if (any(not isinstance(name, str) or name not in canonical_names for name in names)
            or len(set(names)) != len(names) or len(names) > policy['max_images']):
        raise ValueError('Unknown/repeated anchor, or budget cannot give every anchor a turn')
    return ordered


def select_balanced(db, policy, canonical_names, exclude=()):
    ordered = anchors(policy, canonical_names)
    excluded = set(exclude)
    pools, available = {}, {}
    for _, name in ordered:
        available[name] = 0

        def candidates():
            for (image_id,) in db.execute(ELIGIBLE_SQL, (canonical_names[name],)):
                if image_id not in excluded:
                    available[name] += 1
                    yield image_id

        # At most max_images IDs can be consumed globally, so keeping that many
        # per anchor cannot hide a usable candidate. Count the complete stream.
        ranked = heapq.nsmallest(policy['max_images'], candidates(), key=lambda image_id:
                                (hashlib.sha256(f"{policy['seed']}:{image_id}".encode()).digest(), image_id))
        pools[name] = iter(ranked)
    selected, used = [], set(excluded)
    for _ in range(policy['images_per_category']):
        for domain, name in ordered:
            image_id = next((candidate for candidate in pools[name] if candidate not in used), None)
            if image_id is not None:
                used.add(image_id)
                selected.append({'id': image_id, 'selected_domain': domain, 'selected_category': name})
            if len(selected) == policy['max_images']:
                return selected, available
    return selected, available


def run(args):
    root = args.root.resolve()
    for job in (args.catalogue_job, args.prior_selection_job, args.job_id):
        if not re.fullmatch(r'[0-9]+', job):
            raise ValueError('Require actual numeric Slurm job IDs')
    base = root / 'output/training-general-v1'
    source_dir = base / f'catalogue-{args.catalogue_job}'
    prior_dir = base / f'pilot-selection-{args.prior_selection_job}'
    scope_path = base / 'metadata-tools-v1/general-intake-pilot.json'
    db_path = source_dir / 'openimages-train.sqlite'
    exclusion_path = root / 'output/training-0.13/general-smoke-bundle/manifest.json'
    output = base / f'pilot-selection-v2-{args.job_id}'
    report, prior, policy = read(source_dir / 'preparation.json'), read(prior_dir / 'selection-summary.json'), read(scope_path)
    if report['status'] != 'completed' or report['publisher_split'] != 'train':
        raise ValueError('Require a completed publisher-train catalogue')
    if sha(scope_path) != report['scope_sha256'] or sha(db_path) != report['catalogue_sha256']:
        raise ValueError('Source catalogue or scope changed since preparation')
    prior_hash = sha(prior_dir / 'selection.json')
    if (prior['status'] != 'completed' or prior['source_catalogue_job'] != args.catalogue_job
            or prior_hash != prior['selection_sha256'] or prior_hash != args.expected_prior_sha256):
        raise ValueError('Prior selection identity/source does not match verified job')
    prior_selection = read(prior_dir / 'selection.json')
    if prior_selection['scope'] != policy or prior_selection['source']['publisher_split'] != 'train':
        raise ValueError('Prior selection policy/source differs')
    sys.path.insert(0, str(root / 'scripts'))
    from training_data import vocabulary
    canonical_names = {item['canonical_name']: item['canonical_id'] for item in vocabulary()}
    ordered = anchors(policy, canonical_names)
    excluded = {item['id'] if 'id' in item else Path(item['path']).stem
                for item in read(exclusion_path)['images']}
    inv = read(source_dir / 'inventory.json')
    if inv['domains'] != policy['domains'] or inv['raw_labels'] != 601 or inv['canonical_categories'] != 597:
        raise ValueError('Unexpected source inventory/vocabulary')
    if output.exists():
        raise FileExistsError('Preserve existing output; submit a new job')
    print(json.dumps({'status': 'preflight', 'algorithm': ALGORITHM, 'job_id': args.job_id,
                      'source_catalogue_job': args.catalogue_job, 'prior_selection_job': args.prior_selection_job,
                      'anchors': len(ordered), 'max_images': policy['max_images'],
                      'photographs_downloaded': 0, 'approved_for_training': False}, indent=2), flush=True)
    if not args.run:
        return
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
    try:
        source = json.loads(db.execute("SELECT value FROM meta WHERE key='source'").fetchone()[0])
        if source != prior_selection['source'] or source['vocabulary_sha256'] != sha(root / 'dependencies/recognition-vocabulary.json'):
            raise ValueError('Catalogue source or vocabulary differs from frozen contract')
        chosen, available = select_balanced(db, policy, canonical_names, excluded)
    finally:
        db.close()
    counts = Counter(item['selected_category'] for item in chosen)
    domains = Counter(item['selected_domain'] for item in chosen)
    missing = [name for _, name in ordered if not counts[name]]
    coverage_ok = not missing and set(domains) == set(policy['domains']) and len(chosen) == policy['max_images']
    if len({item['id'] for item in chosen}) != len(chosen) or any(item['id'] in excluded for item in chosen):
        raise ValueError('Duplicate IDs or excluded smoke IDs selected')
    # Exclusive new output: neither historical selection nor metadata is edited.
    output.mkdir()
    selection = {'scope': policy, 'source': source, 'algorithm': ALGORITHM, 'images': chosen}
    (output / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(source_dir / 'inventory.json', output / 'inventory.json')
    summary = {'schema': 2, 'status': 'completed' if coverage_ok else 'coverage_failed',
               'job_id': args.job_id, 'algorithm': ALGORITHM,
               'source_catalogue_job': args.catalogue_job, 'prior_selection_job': args.prior_selection_job,
               'publisher_split': 'train', 'selected_candidates': len(chosen),
               'selected_domains': dict(domains), 'selected_anchor_categories': len(counts),
               'requested_anchor_categories': len(ordered), 'anchor_counts': dict(counts),
               'eligible_images_after_exclusions': available,
               'anchor_shortfalls': {name: counts[name] for _, name in ordered if counts[name] < policy['images_per_category']},
               'missing_anchors': missing, 'coverage_gate_passed': coverage_ok,
               'excluded_smoke_ids': len(excluded), 'photographs_downloaded': 0,
               'approved_for_training': False, 'source_catalogue_sha256': report['catalogue_sha256'],
               'scope_sha256': sha(scope_path), 'prior_selection_sha256': prior_hash,
               'exclusion_manifest_sha256': sha(exclusion_path), 'runner_sha256': sha(__file__),
               'training_data_sha256': sha(root / 'scripts/training_data.py'),
               'vocabulary_sha256': source['vocabulary_sha256'],
               'selection_sha256': sha(output / 'selection.json'),
               'inventory_sha256': sha(output / 'inventory.json'),
               'limits': 'Anchors describe acquisition intent, not complete annotations, rights review or accuracy. A 600-image cap cannot give all 52 anchors 12 unique images.'}
    (output / 'selection-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    if not coverage_ok:
        raise ValueError('Coverage gate failed; inspect availability/overlap before image acquisition')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    for option in ('catalogue-job', 'prior-selection-job', 'job-id', 'expected-prior-sha256'):
        parser.add_argument('--' + option, required=True)
    parser.add_argument('--run', action='store_true', help='Persist a metadata-only selection; no network')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
