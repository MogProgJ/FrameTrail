"""Write one reviewed queue block as an immutable decision file.

Argument 1: block name from QUEUE.json. Argument 2: JSON-lines decisions kept outside the repository
during review. Every decision must name a queued image of that block whose original passed the
SHA-256 check in ORIGINALS_RECEIPT.json.
"""
import hashlib, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
DECISIONS = {'absent', 'hold', 'not-absent', 'reject'}


def main():
    block, source = sys.argv[1], pathlib.Path(sys.argv[2])
    queue = json.loads((HERE / 'QUEUE.json').read_text())
    originals = {r['image_id']: r for r in json.loads((HERE / 'ORIGINALS_RECEIPT.json').read_text())['records']}
    entries = {e['image_id']: e for e in queue['entries'] if e['block'] == block}
    rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r['image_id'] in entries]
    if len({r['image_id'] for r in rows}) != len(rows):
        sys.exit('Duplicate decision')
    records = []
    for row in sorted(rows, key=lambda r: entries[r['image_id']]['queue_index']):
        entry = entries[row['image_id']]
        if row['decision'] not in DECISIONS or not originals[row['image_id']]['sha256_matches_inventory']:
            sys.exit(f"Invalid decision or unverified original: {row['image_id']}")
        records.append({
            'queue_index': entry['queue_index'], 'image_id': row['image_id'], 'role': entry['role'],
            'anchor': entry['anchor'], 'image_sha256': entry['sha256'], 'identity_group': entry['identity_group'],
            'decision_133': row['decision'], 'confuser_family': row['family'], 'scene_group': 'scene:' + row['scene'],
            'note': row['note'], 'original_viewed': True, 'original_sha256_verified': True,
            'model_predictions_used': False, 'independent_human_review': False,
            'reviewer': 'assistant (Claude, cloud session)', 'approved_for_training': False,
        })
    complete = len(records) == len(entries)
    output = {
        'schema': 1, 'stage': queue['stage'], 'block': block, 'block_complete': complete,
        'queue_sha256': hashlib.sha256((HERE / 'QUEUE.json').read_bytes()).hexdigest(),
        'task_definition_sha256': queue['pinned_inputs_sha256']['broad-billboard-definition-20261022-v1/TASK_DEFINITION.json'],
        'meaning': {'absent': 'whole photo reviewed; no class133 board under task definition v2',
                    'hold': 'unresolved content or source question; neither absent nor positive',
                    'not-absent': 'contains an in-scope board; positive candidate, boxes not drawn in this stage',
                    'reject': 'excluded by an existing recorded decision or disqualifying source evidence'},
        'records': records,
    }
    target = HERE / f"REVIEW_{block.split('-')[0]}_DECISIONS.json"
    with target.open('x', encoding='utf-8') as handle:
        json.dump(output, handle, indent=1)
        handle.write('\n')
    print(target.name, len(records), 'complete' if complete else 'partial')


if __name__ == '__main__':
    main()
