"""Local, single-image detector comparison. Python is developer tooling only."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union > 0 else 0


def score(truth, predictions, complete=False, threshold=.5):
    """Confidence-ordered, one-to-one, same-class matching at a fixed IoU."""
    remaining = set(range(len(truth)))
    matched = []
    unused = []
    for prediction in sorted(predictions, key=lambda x: x['confidence'], reverse=True):
        candidates = [(iou(prediction['box'], truth[index]['box']), index) for index in remaining
                      if prediction['class_id'] == truth[index]['class_id']]
        overlap, index = max(candidates, default=(0, -1))
        if overlap >= threshold and index >= 0:
            remaining.remove(index)
            matched.append(index)
        else:
            unused.append(prediction)
    # Spatial overlaps are review hints, not proof of a misclassification (objects can overlap).
    hints = []
    for index in sorted(remaining):
        nearby = [p for p in unused if p['class_id'] != truth[index]['class_id'] and iou(p['box'], truth[index]['box']) >= threshold]
        hints.append({'reference': truth[index], 'overlapping_other_labels': nearby})
    return {'targets': len(truth), 'matched': len(matched), 'missed': len(remaining),
            'target_recall': len(matched)/len(truth) if truth else None,
            'predictions': len(predictions),
            'false_positives': len(unused) if complete else None,
            'precision': len(matched)/len(predictions) if complete and predictions else None,
            'unmatched_targets': hints}


def read_manifest(path):
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    if document.get('schema') != 1 or not isinstance(document.get('images'), list) or not document['images']:
        raise ValueError('Expected schema 1 and a nonempty images array')
    for entry in document['images']:
        entry['path'] = (path.parent / entry['path']).resolve(strict=True)
        if type(entry.get('complete')) is not bool or not isinstance(entry.get('objects'), list):
            raise ValueError('Each image needs explicit complete: true/false and objects')
        if any(type(entry.get(k)) is not int or entry[k] <= 0 for k in ('width', 'height')):
            raise ValueError('Each image needs positive integer width and height')
        for item in entry['objects']:
            box = item['box']
            if (type(item['class_id']) is not int or not 0 <= item['class_id'] < 80 or len(box) != 4 or
                    not all(type(v) in (float, int) and math.isfinite(v) for v in box) or
                    not 0 <= box[0] < box[2] <= entry['width'] or not 0 <= box[1] < box[3] <= entry['height']):
                raise ValueError('Invalid COCO contiguous ID or original-image xyxy box')
    return document


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--confidence', type=float, default=.35)
    args = parser.parse_args()
    if not math.isfinite(args.confidence) or not 0 < args.confidence <= 1:
        parser.error('confidence must be in (0,1]')
    manifest = read_manifest(args.manifest.resolve())
    cli = args.cli.resolve(strict=True)
    models = {name: (args.models / filename).resolve(strict=True)
              for name, filename in [('nano', 'yolox_nano.onnx'), ('small', 'yolox_s.onnx')]}
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'confidence': args.confidence, 'nms_iou': .45, 'match_iou': .5,
              'cli_sha256': digest(cli), 'manifest_sha256': digest(args.manifest), 'models': {},
              'notes': 'Selected-image regression only; partial labels cannot establish precision. No mAP, event accuracy or generalization claim. Single-image timing includes first inference, excludes model load.'}
    for name, model in models.items():
        results = []
        for index, entry in enumerate(manifest['images']):
            prefix = args.output / f'{name}-{index:03d}'
            detections, profile, log = [prefix.with_suffix(suffix) for suffix in ('.detections.csv', '.profile.csv', '.log')]
            command = [str(cli), 'inspect', str(entry['path']), '--detect', str(model), '--model-type', name,
                       '--confidence', str(args.confidence), '--max-frames', '2', '--detections', str(detections), '--profile', str(profile)]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
            log.write_text(result.stdout + result.stderr, encoding='utf-8')
            if result.returncode:
                raise RuntimeError(f'Native inference failed; see {log}')
            with profile.open(newline='', encoding='utf-8') as stream:
                frames = list(csv.DictReader(stream))
            if len(frames) != 1 or int(frames[0]['width']) != entry['width'] or int(frames[0]['height']) != entry['height']:
                raise ValueError('Evaluation entries must be single images with matching dimensions')
            with detections.open(newline='', encoding='utf-8') as stream:
                predictions = [{'class_id': int(row['class_id']), 'label': row['label'], 'confidence': float(row['confidence']),
                                'box': [float(row[key]) for key in ('left','top','right','bottom')]} for row in csv.DictReader(stream)]
            metric = score(entry['objects'], predictions, entry['complete'])
            metric.update(image=entry['path'].name, sha256=digest(entry['path']), complete=entry['complete'],
                          pipeline_ms=float(frames[0]['pipeline_ms']))
            results.append(metric)
        targets, matched = sum(r['targets'] for r in results), sum(r['matched'] for r in results)
        report['models'][name] = {'sha256': digest(model), 'images': results, 'targets': targets, 'matched': matched,
                                  'target_recall': matched/targets if targets else None,
                                  'mean_first_frame_pipeline_ms': statistics.mean(r['pipeline_ms'] for r in results)}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for name, result in report['models'].items():
        print(f"{name}: {result['matched']}/{result['targets']} annotated targets matched at IoU 0.5")
    print(f'Report: {args.output / "report.json"}')


if __name__ == '__main__':
    main()
