"""Compare native decoded-YOLO inference against the official Python letterbox + ONNX reference.

Optional developer check. Inputs remain local; this script does not train or download models.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess


def overlap(a, b):
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union > 0 else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--images', nargs='+', type=Path, required=True)
    parser.add_argument('--profiles', nargs='+', choices=('world-s', 'world-m', 'openimages'),
                        default=['world-s', 'world-m', 'openimages'])
    parser.add_argument('--openimages-model', type=Path, help='Optional full-vocabulary training artifact; application models stay unchanged')
    parser.add_argument('--backend', choices=('cpu', 'directml'), default='cpu')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ['YOLO_CONFIG_DIR'] = str(root/'.deps/world-export/config')
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    import cv2
    import numpy as np
    import onnx
    import onnxruntime as ort
    from ultralytics.data.augment import LetterBox
    registry = json.loads((root/'dependencies/recognition-vocabulary.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True, exist_ok=False)
    cli = args.cli.resolve(strict=True)
    report = {'schema': 1, 'reference_runtime': ort.__version__, 'cli_sha256': hashlib.sha256(cli.read_bytes()).hexdigest(), 'checks': {},
              'limits': 'Native bilinear rounding may differ by one intensity unit from OpenCV. Strong targets: >=0.55, IoU >0.98, score delta <0.03. This checks integration, not model accuracy.'}
    filenames = {'world-s': 'yolo_world_s.onnx', 'world-m': 'yolo_world_m.onnx', 'openimages': 'yolo_openimages.onnx'}
    for profile in args.profiles:
        model = args.openimages_model.resolve(strict=True) if profile == 'openimages' and args.openimages_model else root/'models'/filenames[profile]
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 4
        session = ort.InferenceSession(str(model), sess_options=session_options, providers=['CPUExecutionProvider'])
        mapping = list(range(100)) if profile.startswith('world') else registry['openimages_ids']
        checked = 0
        max_score_delta, min_iou = 0., 1.
        for number, image in enumerate(args.images):
            bgr = cv2.imread(str(image.resolve(strict=True)))
            if bgr is None:
                raise ValueError('Unreadable reference image')
            # PNG fixes decoder differences so this comparison isolates inference/pre/postprocessing.
            source = args.output/f'input-{number}.png'
            if not source.exists() and not cv2.imwrite(str(source), bgr):
                raise RuntimeError('Could not create lossless local reference')
            height, width = bgr.shape[:2]
            padded = LetterBox((640, 640), auto=False, scaleup=True)(image=bgr)
            tensor = np.ascontiguousarray(padded[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32)/255
            raw = session.run(None, {session.get_inputs()[0].name: tensor})[0][0].T
            scores = raw[:, 4:].max(axis=1)
            winners = raw[:, 4:].argmax(axis=1)
            rows = np.flatnonzero(scores >= .35)
            ratio = min(640/width, 640/height)
            pad_x, pad_y = (640-round(width*ratio))//2, (640-round(height*ratio))//2
            proposals = []
            for row in rows:
                cx, cy, w, h = raw[row, :4]
                box = [(cx-w/2-pad_x)/ratio, (cy-h/2-pad_y)/ratio,
                       (cx+w/2-pad_x)/ratio, (cy+h/2-pad_y)/ratio]
                box = [float(np.clip(v, 0, width if i % 2 == 0 else height)) for i, v in enumerate(box)]
                if box[2] > box[0] and box[3] > box[1]:
                    proposals.append({'class_id': mapping[int(winners[row])], 'confidence': float(scores[row]), 'box': box})
            kept = []
            for box in sorted(proposals, key=lambda x: x['confidence'], reverse=True):
                if not any(old['class_id'] == box['class_id'] and overlap(old['box'], box['box']) > .45 for old in kept):
                    kept.append(box)
                if len(kept) == 100:
                    break
            output = args.output/f'{profile}-{number}.csv'
            result = subprocess.run([str(cli), 'inspect', str(source.resolve()), '--detect', str(model),
                '--model-type', profile, '--backend', args.backend, '--detections', str(output.resolve())], capture_output=True,
                encoding='utf-8', errors='replace', timeout=90)
            if result.returncode:
                raise RuntimeError(result.stderr)
            expected_provider = 'CPU' if args.backend == 'cpu' else 'DirectML'
            execution = {line.split(': ', 1)[0]: line.split(': ', 1)[1].strip() for line in result.stdout.splitlines()
                         if line.startswith(('Execution provider: ', 'Fallback: '))}
            if execution.get('Execution provider') != expected_provider or execution.get('Fallback'):
                raise AssertionError('Reference comparison did not use the requested native backend')
            with output.open(encoding='utf-8', newline='') as stream:
                actual = [{'class_id': int(r['class_id']), 'confidence': float(r['confidence']),
                    'box': [float(r[k]) for k in ('left','top','right','bottom')]} for r in csv.DictReader(stream)]
            for expected in kept:
                if expected['confidence'] < .55:
                    continue
                choices = [(overlap(expected['box'], p['box']), p) for p in actual if p['class_id'] == expected['class_id']]
                iou, prediction = max(choices, key=lambda x: x[0], default=(0, None))
                delta = abs(expected['confidence']-prediction['confidence']) if prediction else 1
                if iou <= .98 or delta >= .03:
                    raise AssertionError(f'{profile} image {number}: native/reference disagreement: IoU {iou}, score delta {delta}')
                checked += 1
                min_iou, max_score_delta = min(min_iou, iou), max(max_score_delta, delta)
        if checked < 2:
            raise AssertionError(f'{profile}: insufficient strong reference targets')
        # Same shape with wrong labels must fail on both backends before opening exports.
        graph = onnx.load(str(model))
        metadata = {item.key: item.value for item in graph.metadata_props}
        metadata['frametrail.vocabulary'] = 'incorrect\n'+metadata['frametrail.vocabulary']
        onnx.helper.set_model_props(graph, metadata)
        tampered = args.output/f'{profile}-wrong-labels.onnx'
        onnx.save(graph, str(tampered))
        for backend in ['cpu', 'directml']:
            output = args.output/f'{profile}-{backend}-rejected.csv'
            result = subprocess.run([str(cli), 'inspect', str(source.resolve()), '--detect', str(tampered.resolve()),
                '--model-type', profile, '--backend', backend, '--detections', str(output.resolve())],
                capture_output=True, encoding='utf-8', errors='replace', timeout=90)
            if result.returncode == 0 or 'vocabulary' not in result.stderr.lower() or output.exists():
                raise AssertionError(f'{profile}/{backend}: incorrect labels accepted or output reserved')
        report['checks'][profile] = {'strong_targets': checked, 'min_iou': min_iou,
            'max_score_delta': max_score_delta, 'native_backend': args.backend,
            'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'cpu_gpu_wrong_labels_rejected': True}
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
