"""Check actual COCO/YOLO draft files against source-linked correction state."""
import argparse
import json
import math
from pathlib import Path
from annotation_review import load_checked, observation_export, summary
from training_data import contained, digest, read_json, validate_manifest, vocabulary, write_json


def verify(workspace, output):
    output = Path(output).resolve(strict=True)
    source, state = load_checked(workspace, output / 'annotations.json')
    coco, manifest = read_json(output / 'draft-coco.json'), read_json(output / 'draft-manifest.json')
    if coco['info'] != {'purpose': 'annotation-draft-only', 'approved_for_training': False}:
        raise ValueError('COCO draft approval contract changed')
    if coco['categories'] != [{'id': x['raw_id'], 'name': x['name']} for x in vocabulary()]:
        raise ValueError('COCO vocabulary changed')
    if manifest['classes'] != vocabulary() or manifest['approved_for_training'] is not False or manifest['purpose'] != 'annotation-draft-only':
        raise ValueError('Draft manifest contract changed')
    if len(coco['images']) != len(state['images']) or len(manifest['images']) != len(state['images']):
        raise ValueError('Draft image membership changed')
    expected_labels = {x['id'] + '.txt' for x in state['images']}
    if {x.name for x in (output / 'labels').iterdir()} != expected_labels:
        raise ValueError('YOLO label file membership changed')
    annotation_index = 0
    source_root = Path(read_json(Path(workspace) / 'workspace.json')['source_manifest']).parent
    for n, image in enumerate(state['images'], 1):
        ci, mi = coco['images'][n-1], manifest['images'][n-1]
        expected_original = contained(source_root, source['images'][n-1]['path'])
        original = (output / ci['file_name']).resolve()
        if original != expected_original or (output / mi['path']).resolve() != expected_original:
            raise ValueError('Draft references must point to the exact intake photograph')
        if (ci['id'], ci['width'], ci['height'], ci['original_sha256']) != (n, image['width'], image['height'], image['sha256']):
            raise ValueError('COCO image identity/geometry changed')
        if digest(original) != image['sha256'] or digest((output / mi['path']).resolve(strict=True)) != image['sha256']:
            raise ValueError('Draft reference no longer resolves to the original image bytes')
        if mi['id'] != image['id'] or mi['sha256'] != image['sha256'] or mi['split'] != 'unassigned':
            raise ValueError('Draft manifest image identity or partition changed')
        if mi['review']['complete_target_classes'] is not False or mi['review']['rights_verified'] is not False:
            raise ValueError('Draft cannot publish completeness/rights approval')
        active = [x for x in image['objects'] if x['status'] != 'rejected']
        rows = (output / 'labels' / (image['id'] + '.txt')).read_text(encoding='utf-8').splitlines()
        if len(rows) != len(active) or len(mi['objects']) != len(active):
            raise ValueError('YOLO/manifest target count differs from correction state')
        for row, obj, published in zip(rows, active, mi['objects']):
            fields = row.split()
            x1, y1, x2, y2 = obj['box']
            expected = [(x1+x2)/2/image['width'], (y1+y2)/2/image['height'], (x2-x1)/image['width'], (y2-y1)/image['height']]
            values = [float(x) for x in fields[1:]]
            if len(fields) != 5 or fields[0] != str(obj['raw_id']) or any(not math.isfinite(x) or not 0 <= x <= 1 for x in values):
                raise ValueError('Invalid YOLO raw ID/normalized geometry')
            if values[2] <= 0 or values[3] <= 0 or any(abs(x-y) > 1e-8 for x, y in zip(values, expected)):
                raise ValueError('YOLO geometry differs from corrected pixel geometry')
            ca = coco['annotations'][annotation_index]
            if ca['id'] != annotation_index+1 or ca['image_id'] != n or ca['category_id'] != obj['raw_id']:
                raise ValueError('COCO annotation identity mismatch')
            if ca['bbox'] != [x1, y1, x2-x1, y2-y1] or ca['origin'] != obj['origin'] or ca['draft_state'] != obj['status']:
                raise ValueError('COCO target differs from recorded draft')
            if published['box'] != obj['box'] or published['raw_id'] != obj['raw_id'] or published['draft_state'] != obj['status']:
                raise ValueError('Draft manifest target differs from recorded state')
            annotation_index += 1
    if annotation_index != len(coco['annotations']):
        raise ValueError('Extra COCO targets')
    observations_path = output / 'unsupported-observations.json'
    if observations_path.exists():
        if read_json(observations_path) != observation_export(state):
            raise ValueError('Observation sidecar differs from recorded state')
    elif any(image.get('observations') for image in state['images']):
        raise ValueError('Missing unsupported-object observation sidecar')
    if (output / 'data.yaml').exists() or (output / 'dataset-lock.json').exists():
        raise ValueError('Draft directory contains a training-release file')
    try:
        validate_manifest(output / 'draft-manifest.json')
    except ValueError as error:
        rejection = str(error)
    else:
        raise ValueError('Training validator unexpectedly accepted the draft')
    return {**summary(state), 'active_exported_boxes': annotation_index,
            'yolo_files_verified': len(expected_labels), 'coco_photograph_hashes_verified': len(state['images']),
            'training_preflight_rejection': rejection, 'annotations_sha256': digest(output / 'annotations.json'),
            'draft_coco_sha256': digest(output / 'draft-coco.json'),
            'browser_interaction_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--export', dest='output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError('Existing verification report is preserved')
    result = verify(args.workspace, args.output)
    write_json(args.report, result)
    print(json.dumps(result, indent=2))
