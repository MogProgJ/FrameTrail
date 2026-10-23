"""Isolated RF-DETR Small mechanics probe; no training, GUI changes or accuracy approval."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import urllib.request
import uuid

from training_data import digest, read_json, valid_box

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.11.2'
PUBLISHER_COMMIT = '7433d5919d0f7e72cc6cb78663e0a731afd499e0'
PUBLISHER_WHEEL_SHA256 = '2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a'
ASSET_URL = 'https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth'
ASSET_MD5 = 'fb37061c1af7bace359c91b723a8d5c1'
ASSET_BYTES = 386045550  # Verified publisher HEAD on 7 October 2026; checkpoint includes training state.
ASSET_CAP = 400 * 1024 * 1024
ASSET_NAME = 'rf-detr-small.pth'
ASSETS = ROOT / '.deps/rfdetr-probe-assets'
OUTPUTS = ROOT / 'output/rfdetr-probe'
# Official sparse COCO category IDs -> the application's existing 0..79 COCO IDs.
COCO_IDS = (1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,20,21,22,23,24,25,
            27,28,31,32,33,34,35,36,37,38,39,40,41,42,43,44,46,47,48,49,50,51,
            52,53,54,55,56,57,58,59,60,61,62,63,64,65,67,70,72,73,74,75,76,77,
            78,79,80,81,82,84,85,86,87,88,89,90)
COCO_MAP = {raw: canonical for canonical, raw in enumerate(COCO_IDS)}


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_report(path, value):
    # Reports can update within a newly created run; originals/model files never do.
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def md5_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'md5').hexdigest()


def asset_identity(path):
    path = Path(path).resolve(strict=True)
    if path.stat().st_size != ASSET_BYTES or not 0 < path.stat().st_size <= ASSET_CAP or md5_file(path) != ASSET_MD5:
        raise ValueError('Checkpoint does not match the pinned publisher RF-DETR Small asset')
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path),
            'publisher_md5': ASSET_MD5, 'url': ASSET_URL, 'publisher_commit': PUBLISHER_COMMIT,
            'verification': 'Publisher MD5 and local SHA256; MD5 is an integrity check, not a cryptographic authenticity guarantee.'}


def acquire_asset(destination=ASSETS, opener=urllib.request.urlopen):
    destination = Path(destination).resolve()
    if destination != ASSETS.resolve():
        raise ValueError('Model acquisition is restricted to the isolated probe asset directory')
    destination.mkdir(parents=True, exist_ok=True)
    target, receipt = destination / ASSET_NAME, destination / 'acquisition.json'
    if target.exists():
        identity = asset_identity(target)
        if not receipt.is_file() or read_json(receipt).get('sha256') != identity['sha256']:
            raise ValueError('Existing unreceipted/changed checkpoint is preserved; investigate before retrying')
        return read_json(receipt)
    if receipt.exists():
        raise ValueError('Existing acquisition receipt is preserved; checkpoint is missing')
    partial = destination / (ASSET_NAME + '.' + uuid.uuid4().hex + '.partial')
    with opener(urllib.request.Request(ASSET_URL, method='HEAD'), timeout=30) as response:
        if response.geturl() != ASSET_URL:
            raise ValueError('Unexpected publisher redirect')
        expected = int(response.headers['Content-Length'])
        etag = response.headers.get('ETag')
    if expected != ASSET_BYTES or not 0 < expected <= ASSET_CAP:
        raise ValueError('Checkpoint exceeds the explicit download cap')
    count = 0
    try:
        with opener(ASSET_URL, timeout=60) as response, partial.open('xb') as output:
            if response.geturl() != ASSET_URL or int(response.headers['Content-Length']) != expected or response.headers.get('ETag') != etag:
                raise ValueError('Publisher object identity changed between HEAD and GET')
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > expected or count > ASSET_CAP:
                    raise ValueError('Download exceeded its declared byte budget')
                output.write(block)
        if count != expected:
            raise ValueError('Checkpoint download was truncated')
        identity = asset_identity(partial)
        # Refuse concurrent publication; never replace another checkpoint.
        os.link(partial, target)  # Atomic exclusive publication; unlike rename, never replaces an existing target.
        identity['path'] = str(target)
        identity.update(retrieved_at_utc=utc(), etag=etag)
        with receipt.open('x', encoding='utf-8') as output:
            json.dump(identity, output, indent=2)
            output.write('\n')
        partial.unlink()  # Only this run's verified duplicate temporary file.
        return identity
    except Exception:
        # Keep interrupted/corrupt bytes for diagnosis, never delete a user's asset.
        raise


def contract():
    registry = read_json(ROOT / 'dependencies/recognition-vocabulary.json')
    names = registry['classes'][:80]
    if len(names) != 80 or len(set(names)) != 80:
        raise ValueError('Application COCO vocabulary changed')
    return {'schema': 1, 'purpose': 'rfdetr-small-pretrained-mechanics-only', 'approved_for_application': False,
            'trained_by_frametrail': False, 'rfdetr_version': VERSION, 'resolution': 512,
            'input': {'name': 'input', 'shape': [1,3,512,512], 'dtype': 'float32',
                      'color': 'RGB', 'resize': 'bilinear tensor resize, antialias=False, no letterbox',
                      'mean': [0.485,0.456,0.406], 'std': [0.229,0.224,0.225]},
            'outputs': {'boxes': 'dets', 'logits': 'labels', 'logit_slots': 91,
                        'background_class_id': None, 'activation': 'per-class sigmoid',
                        'box_format': 'normalized cxcywh'},
            'classes': [{'raw_slot': raw, 'canonical_id': n, 'name': names[n]} for n, raw in enumerate(COCO_IDS)],
            'limits': '80 COCO categories, not the 597-category broad profile. Not a production/native adapter. No quality claims from unreviewed photographs.'}


def decode_outputs(outputs, width, height, threshold=.35, top_k=300):
    """Mirror the pinned raw query/class-pair decoder, with explicit sparse-ID mapping."""
    import numpy as np
    if set(outputs) != {'dets', 'labels'}:
        raise ValueError('Bind RF-DETR outputs by exact names, never positional order or shape')
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError('Invalid original image dimensions')
    if isinstance(threshold, bool) or not math.isfinite(threshold) or not 0 <= threshold <= 1 or type(top_k) is not int or not 1 <= top_k <= 300:
        raise ValueError('Invalid threshold/top-k budget')
    boxes, logits = np.asarray(outputs['dets']), np.asarray(outputs['labels'])
    if boxes.dtype != np.float32 or logits.dtype != np.float32:
        raise ValueError('Probe expects float32 outputs, not quantized or implicitly converted tensors')
    if boxes.ndim != 3 or boxes.shape[0] != 1 or boxes.shape[2] != 4 or logits.shape != (1, boxes.shape[1], 91):
        raise ValueError('Raw tensors differ from the pinned pretrained Small contract')
    if not np.isfinite(boxes).all() or not np.isfinite(logits).all():
        raise ValueError('Non-finite model output')
    scores = 1 / (1 + np.exp(-np.clip(logits[0], -80, 80)))
    flat = scores.ravel()
    # Stable ordering makes tied test tensors reproducible; production queries rarely tie.
    order = np.argsort(-flat, kind='stable')[:min(top_k, flat.size)]
    result = []
    for pair in order:
        query, raw = divmod(int(pair), 91)
        score = float(flat[pair])
        if score <= threshold or raw not in COCO_MAP:
            continue  # Unused sparse COCO slots are not application categories.
        cx, cy, bw, bh = (float(x) for x in boxes[0,query])
        if bw <= 0 or bh <= 0:
            raise ValueError('Model returned a nonpositive box extent')
        box = [max(0., min(width, (cx-bw/2)*width)), max(0., min(height, (cy-bh/2)*height)),
               max(0., min(width, (cx+bw/2)*width)), max(0., min(height, (cy+bh/2)*height))]
        if valid_box(box, width, height):
            result.append({'class_id': COCO_MAP[raw], 'raw_slot': raw, 'confidence': score, 'box': box})
    return result


def compare_predictions(reference, candidate, minimum=.55, iou_min=.98, score_max=.003):
    from annotation_review import iou
    checked, smallest, largest = 0, 1., 0.
    for source, target in ((reference, candidate), (candidate, reference)):
        used = set()
        for expected in sorted(source, key=lambda x: -x['confidence']):
            if expected['confidence'] < minimum:
                continue
            choices = [(iou(expected['box'], actual['box']), n, actual) for n, actual in enumerate(target)
                       if n not in used and actual['class_id'] == expected['class_id']]
            overlap, n, actual = max(choices, key=lambda x: x[0], default=(0, -1, None))
            delta = abs(expected['confidence']-actual['confidence']) if actual else 1.
            if overlap < iou_min or delta > score_max:
                raise ValueError(f'Reference/export disagreement: IoU={overlap:.6f}, score_delta={delta:.6f}')
            used.add(n)
            checked += 1
            smallest, largest = min(smallest, overlap), max(largest, delta)
    return {'directional_strong_matches': checked, 'minimum_iou': smallest if checked else None,
            'maximum_score_delta': largest if checked else None,
            'limits': 'Numerical integration agreement, not annotation completeness or recognition accuracy.'}


def package_versions():
    versions = {name: importlib.metadata.version(name) for name in
                ('rfdetr','torch','torchvision','onnx','onnxruntime','numpy','pillow')}
    expected = {'rfdetr':VERSION, 'torch':'2.8.0+cpu', 'torchvision':'0.23.0+cpu',
                'onnx':'1.19.1', 'onnxruntime':'1.30.0', 'numpy':'2.2.6', 'pillow':'12.3.0'}
    if versions != expected:
        raise ValueError('Use the pinned isolated RF-DETR CPU probe environment')
    install = read_json(ROOT/'.deps/rfdetr-probe-cpu/pip-install-report.json')
    rf_wheel = next(x for x in install['install'] if x['metadata']['name'].lower() == 'rfdetr')
    if rf_wheel['download_info']['archive_info']['hashes']['sha256'] != PUBLISHER_WHEEL_SHA256:
        raise ValueError('Installed RF-DETR wheel provenance does not match the publisher release')
    return versions


def new_run(path):
    path = Path(path).resolve()
    if path == OUTPUTS.resolve() or not path.is_relative_to(OUTPUTS.resolve()):
        raise ValueError('Run output must be a NEW child of output/rfdetr-probe')
    if path.exists():
        raise FileExistsError('Existing probe results are preserved; choose a new run name')
    path.mkdir(parents=True, exist_ok=False)
    return path


def sdk_predictions(detections, width, height):
    import numpy as np
    ids, scores, boxes = np.asarray(detections.class_id), np.asarray(detections.confidence), np.asarray(detections.xyxy)
    if ids.ndim != 1 or scores.shape != ids.shape or boxes.shape != (ids.size,4) or ids.dtype.kind not in 'iu' or not np.isfinite(boxes).all():
        raise ValueError('Malformed/non-finite SDK prediction arrays')
    names = [x['name'] for x in contract()['classes']]
    result = []
    for raw_slot, confidence, box in zip(ids, scores, boxes):
        raw_slot, confidence = int(raw_slot), float(confidence)
        if raw_slot not in COCO_MAP or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('SDK prediction differs from the pinned publisher sparse COCO-ID mapping')
        class_id = COCO_MAP[raw_slot]
        clipped = [max(0., min(width if n % 2 == 0 else height, float(x))) for n, x in enumerate(box)]
        if valid_box(clipped, width, height):
            result.append({'class_id': class_id, 'raw_slot': raw_slot, 'name': names[class_id], 'confidence': confidence, 'box': clipped})
    return result


def baseline_predictions(cli, photo, output, profile):
    import csv
    import subprocess
    from time import perf_counter
    models = {'small': ROOT/'models/yolox_s.onnx', 'openimages': ROOT/'models/yolo_openimages.onnx'}
    model = models[profile]
    before = digest(model)
    started = perf_counter()
    process = subprocess.run([str(Path(cli).resolve(strict=True)), 'inspect', str(photo), '--max-frames','1',
        '--detect',str(model), '--model-type',profile, '--backend','cpu', '--confidence','0.35',
        '--detections',str(output)], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    elapsed = perf_counter()-started
    execution = {line.split(': ',1)[0]:line.split(': ',1)[1].strip() for line in process.stdout.splitlines()
                 if line.startswith(('Execution provider: ', 'Fallback: '))}
    if process.returncode or execution.get('Execution provider') != 'CPU' or execution.get('Fallback', 'unreported'):
        raise RuntimeError('Native baseline failed to use its requested CPU backend: ' + process.stderr[-1000:])
    if digest(model) != before:
        raise ValueError('An existing application model changed')
    predictions = []
    with Path(output).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            predictions.append({'class_id':int(row['class_id']), 'confidence':float(row['confidence']),
                                'box':[float(row[key]) for key in ('left','top','right','bottom')]})
    return {'profile':profile, 'model_sha256':before, 'cli_sha256':digest(cli), 'execution':execution, 'predictions':predictions,
            'wall_seconds_including_process_model_load_and_decode':elapsed,
            'limits':'Separate prediction output, not accuracy or comparable warm model-only latency.'}


def run_probe(manifest, checkpoint, output, count=6, baseline_cli=None):
    import platform
    import sys
    from time import perf_counter
    from annotation_review import check_intake
    if type(count) is not int or not 1 <= count <= 12:
        raise ValueError('Probe must be bounded to 1..12 photographs')
    manifest = Path(manifest).resolve(strict=True)
    source = check_intake(manifest)
    if count > len(source['images']):
        raise ValueError('Requested more images than the intake contains')
    identity, versions = asset_identity(checkpoint), package_versions()
    checkpoint = Path(checkpoint).resolve(strict=True)
    if checkpoint != (ASSETS/ASSET_NAME).resolve() or read_json(ASSETS/'acquisition.json')['sha256'] != identity['sha256']:
        raise ValueError('Use the receipted isolated publisher checkpoint')
    output = new_run(output)
    import shutil
    snapshot = output/'source-snapshot'
    snapshot.mkdir()
    for name in ('rfdetr_probe.py','probe-rfdetr.py','requirements-rfdetr-probe.txt','setup-rfdetr-probe.ps1'):
        shutil.copy2(ROOT/'scripts'/name, snapshot/name)
    shutil.copy2(ROOT/'.deps/rfdetr-probe-cpu/installed-packages.txt',output/'installed-packages.txt')
    shutil.copy2(ROOT/'.deps/rfdetr-probe-cpu/pip-install-report.json',output/'pip-install-report.json')
    report_path = output / 'experiment.json'
    model_contract = contract()
    report = {'schema':1, 'purpose':'pretrained-inference-export-mechanics-only', 'status':'running',
        'approved_for_application':False, 'training_performed':False, 'accuracy_evaluated':False,
        'native_rf_adapter_implemented':False, 'directml_evaluated':False,
        'started_at_utc':utc(), 'source_manifest_sha256':digest(manifest), 'checkpoint':identity,
        'environment':{'python':sys.version, 'platform':platform.platform(), 'packages':versions},
        'environment_snapshot_sha256':digest(output/'installed-packages.txt'),
        'source_hashes':{name:digest(ROOT/'scripts'/name) for name in
                         ('rfdetr_probe.py','probe-rfdetr.py','requirements-rfdetr-probe.txt')},
        'contract':model_contract, 'images':[],
        'limits':'These unreviewed publisher-train photographs are mechanics inputs, not independent deployment evaluation. Prediction counts, confidence and export parity are not accuracy.'}
    write_report(report_path, report)
    try:
        # Keep every optional library cache local. No home-cache or hidden backbone/weight download.
        cache = output/'cache'
        for name, folder in (('HF_HOME','huggingface'),('MPLCONFIGDIR','matplotlib'),('TORCH_HOME','torch')):
            os.environ[name] = str(cache/folder)
        os.environ.update(RF_HOME=str(ASSETS), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
        import numpy as np
        import torch
        import torchvision.transforms.functional as transforms
        from PIL import Image
        from rfdetr import RFDETRSmall
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        print('Loading receipted RF-DETR Small on CPU (no training).', flush=True)
        started = perf_counter()
        model = RFDETRSmall(pretrain_weights=str(checkpoint), device='cpu')
        report['model_load_seconds'] = perf_counter()-started
        if model.model_config.resolution != 512:
            raise ValueError('Small model resolution changed')
        (output/'inputs').mkdir()
        (output/'torch-raw').mkdir()
        first_photo = manifest.parent/source['images'][0]['path']
        with Image.open(first_photo) as photo:
            model.predict(photo.convert('RGB'), threshold=.35)  # One warmup, excluded from reported timings.
        for n, item in enumerate(source['images'][:count]):
            print(f'RF-DETR photo {n+1}/{count}: {item["id"]}', flush=True)
            original = manifest.parent/item['path']
            with Image.open(original) as decoded:
                photo = decoded.convert('RGB')
            input_png = output/'inputs'/(item['id']+'.png')
            photo.save(input_png)
            started = perf_counter()
            sdk = model.predict(photo, threshold=.35)
            sdk_ms = (perf_counter()-started)*1000
            reference = sdk_predictions(sdk, item['width'], item['height'])
            tensor = transforms.to_tensor(photo)
            tensor = transforms.resize(tensor, [512,512], antialias=False)
            tensor = transforms.normalize(tensor, model_contract['input']['mean'], model_contract['input']['std']).unsqueeze(0)
            started = perf_counter()
            with torch.inference_mode():
                raw = model.model.model(tensor)
            forward_ms = (perf_counter()-started)*1000
            raw_arrays = {'dets':raw['pred_boxes'].detach().numpy(), 'labels':raw['pred_logits'].detach().numpy()}
            custom = decode_outputs(raw_arrays, item['width'], item['height'])
            sdk_check = compare_predictions(reference, custom)
            np.savez_compressed(output/'torch-raw'/(item['id']+'.npz'), **raw_arrays)
            np.save(output/'inputs'/(item['id']+'.npy'), tensor.numpy(), allow_pickle=False)
            record = {'image_id':item['id'], 'original_sha256':item['sha256'], 'width':item['width'], 'height':item['height'],
                'rf_sdk_predictions':reference, 'rf_sdk_end_to_end_ms_excluding_file_decode':sdk_ms,
                'rf_torch_forward_only_ms':forward_ms, 'sdk_decoder_parity':sdk_check}
            if baseline_cli:
                record['baselines'] = [baseline_predictions(baseline_cli, input_png, output/(profile+'-'+item['id']+'.csv'), profile)
                                       for profile in ('small','openimages')]
            report['images'].append(record)
            write_report(report_path, report)
        print('Exporting static float32 ONNX to the isolated probe output.', flush=True)
        started = perf_counter()
        export_path = Path(model.export(output_dir=str(output/'onnx'), format='onnx', opset_version=17,
            shape=(512,512), batch_size=1, dynamic_batch=False, verbose=False, fp16=False)).resolve(strict=True)
        if not export_path.is_relative_to(output):
            raise ValueError('Exporter wrote outside its isolated run')
        report['export_seconds'] = perf_counter()-started
        import onnx
        import onnxruntime as ort
        graph = onnx.load(str(export_path))
        onnx.checker.check_model(graph, full_check=True)
        graph_info = {'frametrail.probe_only':'true', 'frametrail.rf_contract':json.dumps(model_contract, separators=(',',':'))}
        onnx.helper.set_model_props(graph, graph_info)
        onnx.save(graph, str(export_path))
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(export_path), sess_options=options, providers=['CPUExecutionProvider'])
        inputs, outputs = session.get_inputs(), session.get_outputs()
        if len(inputs) != 1 or inputs[0].name != 'input' or inputs[0].shape != [1,3,512,512] or inputs[0].type != 'tensor(float)':
            raise ValueError('ONNX input differs from the frozen probe contract')
        if {x.name for x in outputs} != {'dets','labels'} or any(x.type != 'tensor(float)' for x in outputs):
            raise ValueError('ONNX outputs differ from the explicit named float32 contract')
        report['export'] = {'path':str(export_path), 'sha256':digest(export_path), 'bytes':export_path.stat().st_size,
                            'providers':session.get_providers(), 'outputs':{x.name:x.shape for x in outputs}}
        strong_matches = 0
        for record in report['images']:
            image_id = record['image_id']
            tensor = np.load(output/'inputs'/(image_id+'.npy'), allow_pickle=False)
            session.run(['dets','labels'], {'input':tensor})  # Per-image warmup excluded.
            started = perf_counter()
            boxes, logits = session.run(['dets','labels'], {'input':tensor})
            record['rf_ort_forward_only_ms'] = (perf_counter()-started)*1000
            with np.load(output/'torch-raw'/(image_id+'.npz'), allow_pickle=False) as reference:
                box_delta = float(np.max(np.abs(boxes-reference['dets'])))
                logit_delta = float(np.max(np.abs(logits-reference['labels'])))
            if box_delta > .0001 or logit_delta > .001:
                raise ValueError(f'Raw PyTorch/ONNX tensor parity failed: box={box_delta}, logit={logit_delta}')
            predictions = decode_outputs({'dets':boxes,'labels':logits}, record['width'], record['height'])
            check = compare_predictions(record['rf_sdk_predictions'], predictions)
            record.update(rf_onnx_predictions=predictions, export_parity=check,
                          raw_box_max_abs_delta=box_delta, raw_logit_max_abs_delta=logit_delta)
            strong_matches += check['directional_strong_matches']
        if strong_matches < 4:
            raise ValueError('Too few strong reference predictions to establish non-vacuous integration parity')
        if digest(manifest) != report['source_manifest_sha256'] or asset_identity(checkpoint)['sha256'] != identity['sha256']:
            raise ValueError('Immutable probe input changed during the run')
        check_intake(manifest)  # Recheck all original image bytes/geometry after the probe.
        report.update(status='completed', finished_at_utc=utc(), sdk_and_onnx_cpu_parity_passed=True,
                      directional_strong_matches=strong_matches)
        write_report(report_path, report)
        return report
    except Exception as error:
        report.update(status='failed', finished_at_utc=utc(), error=str(error), sdk_and_onnx_cpu_parity_passed=False)
        write_report(report_path, report)
        raise
