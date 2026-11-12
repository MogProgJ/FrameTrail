"""Make the trained model's scores mean the same thing for every class.

Open Images labels are incomplete and one object can carry several labels (a bowl of salad is Bowl, Salad or Food),
so the trained RF-DETR gives many correct boxes a low score: on the user's clips a Bowl box scoring 0.15 is nearly
always right, while a Person box scoring 0.15 is usually wrong. mAP cannot see this, because it only ranks boxes
within one class. The app, however, applies one confidence setting to all classes.

This tool measures, per class, how often a box with a given raw score is right on human-verified images and fits
    calibrated = sigmoid(slope * logit(raw) + offset)
so that a calibrated score is an estimate of "chance this box is right". The app reads the table from
<model>.calibration.csv next to the model and applies it before its confidence setting (src/rfdetr.cpp).

Two steps (the first needs onnxruntime, numpy and Pillow; the second numpy only):

    python training/calibrate.py predict --model models/rfdetr_openimages.onnx --images data/full/valid \\
        --out runs/round3/calibration-valid.jsonl
    python training/calibrate.py fit --predictions runs/round3/calibration-valid.jsonl \\
        --annotations data/full/valid/_annotations.coco.json --out models/rfdetr_openimages.calibration.csv

Fit on the validation split, never on test. Classes with little evidence are pulled towards the curve of all classes
together; `--others keep` leaves classes without any evidence unchanged instead.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import oi_metric

HERE = Path(__file__).resolve().parent
VOCABULARY_PATHS = (HERE.parent / 'dependencies' / 'recognition-vocabulary.json', HERE / 'recognition-vocabulary.json')
INPUT = 512
QUERIES = 300
FLOOR = 0.02      # Boxes below this raw score are not used: far under anything the app shows.
NMS_IOU = 0.45    # The app's class-wise NMS.
PRIOR_WEIGHT = 30.0  # How strongly a class with little evidence is held to the all-class curve.
SLOPE_RANGE = (0.3, 3.0)
OFFSET_RANGE = (-6.0, 6.0)
BANDS = ((0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.7), (0.7, 1.01))


def load_vocabulary(path: Path | None = None) -> dict:
    for candidate in ([path] if path else VOCABULARY_PATHS):
        if candidate and candidate.exists():
            return json.loads(candidate.read_text(encoding='utf-8'))
    raise SystemExit('recognition-vocabulary.json not found')


def app_ids(names: list[str], vocabulary: dict) -> list[int | None]:
    """App category ID per dataset class name, as export.py places them."""
    by_label = {label.lower(): cid for label, cid in zip(vocabulary['openimages_labels'], vocabulary['openimages_ids'])}
    by_name = {name.lower(): cid for cid, name in enumerate(vocabulary['classes'])}
    return [by_label.get(name.lower(), by_name.get(name.lower())) for name in names]


# ---------------------------------------------------------------- predict

def preprocess(image):
    """The app's transform (src/rfdetr.cpp): bilinear resize to 512x512 with half-pixel centres, ImageNet normalisation."""
    import numpy as np
    height, width = image.shape[:2]
    ys = np.clip((np.arange(INPUT) + .5) * height / INPUT - .5, 0, height - 1)
    xs = np.clip((np.arange(INPUT) + .5) * width / INPUT - .5, 0, width - 1)
    y0, x0 = ys.astype(int), xs.astype(int)
    y1, x1 = np.minimum(y0 + 1, height - 1), np.minimum(x0 + 1, width - 1)
    fy, fx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    pixels = image.astype(np.float32) / 255
    top = pixels[y0][:, x0] * (1 - fx) + pixels[y0][:, x1] * fx
    bottom = pixels[y1][:, x0] * (1 - fx) + pixels[y1][:, x1] * fx
    mean, std = np.array([.485, .456, .406], np.float32), np.array([.229, .224, .225], np.float32)
    return (((top * (1 - fy) + bottom * fy) - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)


def decode(output, width: int, height: int, floor: float = FLOOR) -> list[tuple[int, float, list[float]]]:
    """The app's decoding (top 300 class scores, class-wise NMS) down to `floor`: [(app class, raw score, box)]."""
    import numpy as np
    flat = output.reshape(QUERIES, -1)
    probability = 1 / (1 + np.exp(-np.clip(flat[:, 4:], -50, 50)))
    query, cls = np.where(probability >= floor)
    order = np.argsort(-probability[query, cls], kind='stable')[:300]
    kept: list[tuple[int, float, list[float]]] = []
    for i in order:
        cx, cy, w, h = flat[query[i], :4]
        box = [float(min(max((cx - w / 2) * width, 0), width)), float(min(max((cy - h / 2) * height, 0), height)),
               float(min(max((cx + w / 2) * width, 0), width)), float(min(max((cy + h / 2) * height, 0), height))]
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        cid = int(cls[i])
        if any(k[0] == cid and oi_metric._iou(k[2], box) > NMS_IOU for k in kept):
            continue
        kept.append((cid, float(probability[query[i], cls[i]]), box))
    return kept


def predict(args) -> int:
    import numpy as np
    import onnxruntime
    from PIL import Image
    session = onnxruntime.InferenceSession(str(args.model), providers=['CPUExecutionProvider'])
    name = session.get_inputs()[0].name
    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    done = set()
    if args.out.exists():  # Resumable: one line per finished image.
        done = {json.loads(line)['image'] for line in args.out.read_text(encoding='utf-8').splitlines() if line.strip()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('a', encoding='utf-8') as handle:
        for number, path in enumerate(files, 1):
            if path.name in done:
                continue
            with Image.open(path) as image:
                pixels = np.asarray(image.convert('RGB'))
            output = session.run(None, {name: preprocess(pixels)})[0]
            detections = decode(output, pixels.shape[1], pixels.shape[0])
            handle.write(json.dumps({'image': path.name, 'detections': [[c, round(s, 5), [round(v, 1) for v in b]]
                                                                        for c, s, b in detections]}) + '\n')
            if number % 200 == 0:
                handle.flush()
                print(f'{number}/{len(files)}', flush=True)
    print(f'{args.out}: {len(files)} images')
    return 0


# ---------------------------------------------------------------- fit

def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def apply(curve: tuple[float, float], raw: float) -> float:
    return sigmoid(curve[0] * logit(raw) + curve[1])


def raw_for(calibrated: float, curve: tuple[float, float]) -> float:
    """Raw score that the curve maps to `calibrated`."""
    return sigmoid((logit(calibrated) - curve[1]) / curve[0])


def fit_curve(samples: list[tuple[float, bool]], prior: tuple[float, float] | None, weight: float) -> tuple[float, float]:
    """Logistic fit of right/wrong on logit(raw score), pulled towards `prior` (slope, offset) with strength `weight`."""
    import numpy as np
    if not samples:
        return prior if prior else (1.0, 0.0)
    z = np.array([logit(s) for s, _ in samples])
    y = np.array([float(t) for _, t in samples])
    slope, offset = prior if prior else (1.0, 0.0)
    for _ in range(100):  # Damped Newton steps on the penalised log-likelihood; two parameters, so this converges fast.
        p = 1 / (1 + np.exp(-np.clip(slope * z + offset, -30, 30)))
        gradient = np.array([np.sum((p - y) * z), np.sum(p - y)])
        w = p * (1 - p)
        hessian = np.array([[np.sum(w * z * z), np.sum(w * z)], [np.sum(w * z), np.sum(w)]])
        if prior:
            gradient += weight * np.array([slope - prior[0], offset - prior[1]])
            hessian += weight * np.eye(2)
        hessian += 1e-6 * np.eye(2)
        step = np.clip(np.linalg.solve(hessian, gradient), -1.0, 1.0)
        slope = min(max(slope - step[0], SLOPE_RANGE[0]), SLOPE_RANGE[1])
        offset = min(max(offset - step[1], OFFSET_RANGE[0]), OFFSET_RANGE[1])
        if abs(step[0]) < 1e-6 and abs(step[1]) < 1e-6:
            break
    return float(slope), float(offset)


def scored_boxes(truth: dict, class_ids: dict[int, int | None], predictions: dict[str, list]) -> dict[int, list[tuple[float, bool]]]:
    """Dataset class -> [(raw score, right?)] on images where that class was human-verified (the evaluator's rule)."""
    samples: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for file_name, image in truth.items():
        if file_name not in predictions:
            continue
        by_class = defaultdict(list)
        for cid, score, box in predictions[file_name]:
            by_class[cid].append((score, box))
        for cat in image.positive | image.negative:
            app = class_ids.get(cat)
            if app is None:
                continue
            boxes = [(b[1], b[2], b[3], b[4], b[5]) for b in image.boxes if b[0] == cat]
            samples[cat].extend(oi_metric._score_image(by_class.get(app, []), boxes, 0.5))
    return samples


def banded(pairs: list[tuple[float, bool]]) -> list[tuple[str, int, float]]:
    """[(band, boxes, share right)] over bands of the score."""
    rows = []
    for low, high in BANDS:
        inside = [t for c, t in pairs if low <= c < high]
        if inside:
            rows.append((f'{low:.2f}-{min(high, 1):.2f}', len(inside), sum(inside) / len(inside)))
    return rows


def read_predictions(path: Path) -> dict[str, list]:
    rows = (json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())
    return {row['image']: [(c, s, tuple(b)) for c, s, b in row['detections'] if s >= FLOOR] for row in rows}


def gather(prediction_paths, annotation_paths, vocabulary: dict) -> tuple[dict[int, list[tuple[float, bool]]], int]:
    """App class -> scored boxes over several (predictions, annotations) pairs, and the number of images used."""
    samples: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    images = 0
    for prediction_path, annotation_path in zip(prediction_paths or [], annotation_paths or []):
        truth, categories = oi_metric.truth_from_coco(json.loads(annotation_path.read_text(encoding='utf-8')))
        ids = dict(zip(categories, app_ids(list(categories.values()), vocabulary)))
        predictions = read_predictions(prediction_path)
        images += sum(name in predictions for name in truth)
        for cat, rows in scored_boxes(truth, ids, predictions).items():
            samples[ids[cat]].extend(rows)
    return samples, images


def fit(args) -> int:
    vocabulary = load_vocabulary(args.vocabulary)
    names = vocabulary['classes']
    samples, images = gather(args.predictions, args.annotations, vocabulary)
    held, _ = gather(args.check_predictions, args.check_annotations, vocabulary)
    pooled = [row for rows in samples.values() for row in rows]
    if not pooled:
        raise SystemExit('No scored boxes: do the predictions and annotations belong together?')
    overall = fit_curve(pooled, None, 0.0)
    curves: dict[int, tuple[float, float]] = {}
    for app, rows in samples.items():
        if len(rows) < 5:
            continue  # Nothing to learn from; treated like a class without evidence.
        curves[app] = fit_curve(rows, overall, PRIOR_WEIGHT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['class_id', 'slope', 'offset', 'boxes', 'right', 'label'])  # The app reads the first three.
        for app in range(len(names)):
            rows = samples.get(app, [])
            if app in curves:
                curve = curves[app]
            elif args.others == 'pooled':
                curve = overall
            else:
                continue
            writer.writerow([app, f'{curve[0]:.4f}', f'{curve[1]:.4f}', len(rows), sum(t for _, t in rows), names[app]])
    report = {'images': images, 'boxes': len(pooled), 'right': sum(t for _, t in pooled),
              'all_classes': {'slope': overall[0], 'offset': overall[1]}, 'others': args.others, 'classes': {}}
    lines = [f'Calibration from {images} images, {len(pooled)} scored boxes ({report["right"]} right), {len(curves)} classes fitted.',
             f'All classes together: slope {overall[0]:.2f}, offset {overall[1]:+.2f}; a raw score of '
             f'{raw_for(0.35, overall):.2f} becomes 0.35 and {raw_for(0.5, overall):.2f} becomes 0.5.', '',
             '| class | boxes | right | raw score that becomes 0.35 | becomes 0.5 | check: calibrated band, boxes, share right |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for app in sorted(curves, key=lambda a: -len(samples[a])):
        rows, curve = samples[app], curves[app]
        check = held.get(app) or rows
        bands = '; '.join(f'{band}: {count}, {share:.0%}' for band, count, share in banded([(apply(curve, s), t) for s, t in check]))
        lines.append(f'| {names[app]} | {len(rows)} | {sum(t for _, t in rows)} | {raw_for(0.35, curve):.2f} | '
                     f'{raw_for(0.5, curve):.2f} | {bands} |')
        report['classes'][names[app]] = {'slope': curve[0], 'offset': curve[1], 'boxes': len(rows), 'right': sum(t for _, t in rows),
                                         'raw_for_0.35': raw_for(0.35, curve), 'raw_for_0.5': raw_for(0.5, curve)}
    checked = [(a, s, t) for a, rows in held.items() if a in curves for s, t in rows]
    if checked:
        lines += ['', f'Held-out check ({len(checked)} boxes on images not used for the fit), by calibrated score:']
        lines += [f'  {band}: {count} boxes, {share:.0%} right' for band, count, share in banded([(apply(curves[a], s), t) for a, s, t in checked])]
        lines.append('The same boxes by raw score:')
        lines += [f'  {band}: {count} boxes, {share:.0%} right' for band, count, share in banded([(s, t) for _, s, t in checked])]
    text = '\n'.join(lines)
    args.out.with_suffix('.md').write_text(text + '\n', encoding='utf-8')
    args.out.with_suffix('.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('predict', help='run the app model on a folder of images, keeping low scores')
    run.add_argument('--model', type=Path, required=True)
    run.add_argument('--images', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.set_defaults(action=predict)
    learn = commands.add_parser('fit', help='fit the per-class score curves')
    learn.add_argument('--predictions', type=Path, nargs='+', required=True)
    learn.add_argument('--annotations', type=Path, nargs='+', required=True, help='_annotations.coco.json per predictions file')
    learn.add_argument('--check-predictions', type=Path, nargs='*', help='held-out predictions for the report')
    learn.add_argument('--check-annotations', type=Path, nargs='*')
    learn.add_argument('--others', choices=('pooled', 'keep'), default='pooled',
                       help='classes without evidence: the all-class curve (default) or unchanged')
    learn.add_argument('--vocabulary', type=Path)
    learn.add_argument('--out', type=Path, required=True, help='<model>.calibration.csv')
    learn.set_defaults(action=fit)
    args = parser.parse_args(argv)
    if args.command == 'fit' and len(args.predictions) != len(args.annotations):
        parser.error('one --annotations file per --predictions file')
    return args.action(args)


if __name__ == '__main__':
    sys.exit(main())
