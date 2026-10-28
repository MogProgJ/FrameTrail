"""Score a detector on one split of a dataset built by openimages.py.

Backends:
    rfdetr       a checkpoint written by train.py (or any RF-DETR .pth)
    ultralytics  e.g. yolov8s-oiv7.pt, the Open Images model the app already ships (baseline)

Predicted class names are mapped onto our categories by target name or by any merged
Open Images source name (case-insensitive). Unmapped predictions are dropped.

Next to the flat score, `hierarchy` holds a parent-aware one in which a child class also counts as its
parents (a Dog box is also an Animal box), as the Open Images Challenge scores; see hierarchy.py.

Examples:
    python training/evaluate.py --dataset data/pilot --backend rfdetr \
        --weights runs/pilot-small/checkpoint_best_total.pth --out runs/pilot-small/eval-test.json
    python training/evaluate.py --dataset data/pilot --backend ultralytics \
        --weights yolov8s-oiv7.pt --out runs/baseline-yolov8s-oiv7/eval-test.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hierarchy  # noqa: E402
import oi_metric  # noqa: E402

PEOPLE_AND_VEHICLES = ['Person', 'Car', 'Bus', 'Truck', 'Van', 'Motorcycle', 'Bicycle']
MERGE_NMS_IOU = 0.7  # After mapping, e.g. a baseline's Man and Person boxes on one person become one Person.


def name_map(dataset: Path, categories: dict[int, str]) -> dict[str, int]:
    """Lower-cased target and source names -> category id."""
    mapping = {name.lower(): cat for cat, name in categories.items()}
    summary = dataset / 'dataset.json'
    if summary.exists():
        for entry in json.loads(summary.read_text(encoding='utf-8'))['classes']:
            for source in entry['open_images']:
                mapping[source.lower()] = entry['id']
    return mapping


def parent_aware(dataset: Path, cache: Path, truth: dict, detections: dict, categories: dict[int, str]) -> dict | None:
    """The same scoring with the Open Images class hierarchy applied (hierarchy.py), or None if unavailable."""
    ancestors = hierarchy.for_dataset(dataset, cache)
    if not ancestors:
        return None
    expanded = {image: suppress_duplicates(items)
                for image, items in hierarchy.expand_detections(detections, ancestors).items()}
    result = oi_metric.evaluate(hierarchy.expand_truth(truth, ancestors), expanded, categories)
    result['map50_people_and_vehicles'] = oi_metric.subset_map(result, PEOPLE_AND_VEHICLES)
    result['classes_with_parents'] = sum(1 for above in ancestors.values() if above)
    return result


def suppress_duplicates(items: list[tuple[int, float, tuple]]) -> list[tuple[int, float, tuple]]:
    """Class-wise NMS on mapped detections so merged source classes cannot double-count one object."""
    kept: list[tuple[int, float, tuple]] = []
    for cat, score, box in sorted(items, key=lambda d: -d[1]):
        if all(k[0] != cat or oi_metric._iou(k[2], box) <= MERGE_NMS_IOU for k in kept):
            kept.append((cat, score, box))
    return kept


def predict_rfdetr(weights: Path, paths: list[Path], threshold: float, batch: int, size: str):
    import rfdetr
    model_class = {'nano': rfdetr.RFDETRNano, 'small': rfdetr.RFDETRSmall, 'medium': rfdetr.RFDETRMedium,
                   'base': rfdetr.RFDETRBase, 'large': rfdetr.RFDETRLarge}[size]
    from checkpoints import head_classes
    model = model_class(pretrain_weights=str(weights), num_classes=head_classes(weights))
    for start in range(0, len(paths), batch):
        chunk = paths[start:start + batch]
        results = model.predict([str(p) for p in chunk], threshold=threshold, include_source_image=False)
        if not isinstance(results, list):
            results = [results]
        for path, detections in zip(chunk, results):
            # rfdetr attaches names itself; it handles COCO-sparse ids and the no-object slot ("__background__").
            names = detections.data.get('class_name', [])
            yield path.name, [(str(n), float(s), tuple(float(v) for v in box))
                              for box, n, s in zip(detections.xyxy, names, detections.confidence)
                              if n and n != '__background__']


def predict_ultralytics(weights: Path, paths: list[Path], threshold: float, batch: int, size: str):
    from ultralytics import YOLO
    model = YOLO(str(weights))
    for start in range(0, len(paths), batch):
        chunk = paths[start:start + batch]
        for path, result in zip(chunk, model.predict([str(p) for p in chunk], conf=threshold, max_det=300,
                                                      verbose=False)):
            boxes = result.boxes
            yield path.name, [(result.names[int(c)], float(s), tuple(float(v) for v in box))
                              for box, c, s in zip(boxes.xyxy.tolist(), boxes.cls.tolist(), boxes.conf.tolist())]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--split', default='test', choices=('train', 'valid', 'test'))
    parser.add_argument('--backend', choices=('rfdetr', 'ultralytics'))
    parser.add_argument('--weights', type=Path)
    parser.add_argument('--model-size', default='small', help='RF-DETR size the checkpoint was trained with')
    parser.add_argument('--predictions', type=Path, help='re-score saved predictions instead of running a model')
    parser.add_argument('--out', type=Path, required=True, help='metrics JSON; predictions go beside it')
    parser.add_argument('--threshold', type=float, default=0.01, help='low, so AP sees the whole score range')
    parser.add_argument('--batch', type=int, default=8)
    parser.add_argument('--limit', type=int, help='only the first N images (quick checks)')
    parser.add_argument('--cache', type=Path, default=Path('data/openimages-metadata'),
                        help='Open Images metadata folder (class hierarchy and names for the parent-aware score)')
    args = parser.parse_args(argv)

    folder = args.dataset / args.split
    coco = json.loads((folder / '_annotations.coco.json').read_text(encoding='utf-8'))
    truth, categories = oi_metric.truth_from_coco(coco)
    names = name_map(args.dataset, categories)
    files = sorted(truth)[:args.limit] if args.limit else sorted(truth)
    truth = {f: truth[f] for f in files}

    started = time.time()
    if args.predictions:
        raw = {row['image']: [(d[0], d[1], tuple(d[2])) for d in row['detections']]
               for row in map(json.loads, args.predictions.read_text(encoding='utf-8').splitlines())}
        source = str(args.predictions)
    else:
        if not args.backend or not args.weights:
            parser.error('--backend and --weights are required unless --predictions is given')
        predict = predict_rfdetr if args.backend == 'rfdetr' else predict_ultralytics
        raw = {}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        saved = args.out.with_name(args.out.stem + '-predictions.jsonl')
        with saved.open('w', encoding='utf-8') as handle:
            for done, (image, detections) in enumerate(
                    predict(args.weights, [folder / f for f in files], args.threshold, args.batch, args.model_size), 1):
                raw[image] = detections
                handle.write(json.dumps({'image': image, 'detections': detections}) + '\n')
                if done % 500 == 0:
                    print(f'{done}/{len(files)} images', flush=True)
        source = str(saved)

    detections, unmapped = {}, set()
    for image, items in raw.items():
        mapped = []
        for name, score, box in items:
            cat = names.get(str(name).lower())
            if cat is None:
                unmapped.add(str(name))
            else:
                mapped.append((cat, score, box))
        detections[image] = suppress_duplicates(mapped)

    result = oi_metric.evaluate(truth, detections, categories)
    result.update({
        'map50_people_and_vehicles': oi_metric.subset_map(result, PEOPLE_AND_VEHICLES),
        'dataset': str(args.dataset), 'split': args.split, 'images': len(truth),
        'backend': args.backend, 'weights': str(args.weights) if args.weights else None,  # Also with --predictions.
        'predictions': source, 'threshold': args.threshold,
        'unmapped_prediction_classes': len(unmapped), 'seconds': round(time.time() - started, 1)})
    with_parents = parent_aware(args.dataset, args.cache, truth, detections, categories)
    if with_parents:
        result['hierarchy'] = with_parents
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1), encoding='utf-8')
    worst = sorted((v['ap'], k) for k, v in result['per_class'].items() if v['ap'] is not None)[:5]
    print(f"mAP@0.5 {result['map50']:.4f} over {result['classes_scored']} classes; "
          f"people/vehicles {result['map50_people_and_vehicles'] or 0:.4f}; "
          f"weakest: {', '.join(f'{n} {a:.2f}' for a, n in worst)}")
    if with_parents:
        print(f"With parent classes (Open Images hierarchy): mAP@0.5 {with_parents['map50']:.4f}; "
              f"people/vehicles {with_parents['map50_people_and_vehicles'] or 0:.4f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
