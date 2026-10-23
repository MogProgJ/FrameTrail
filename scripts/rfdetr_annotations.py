"""Bounded offline RF-DETR proposal catalogues; human adoption, never training approval."""
import copy
import hashlib
import math
from pathlib import Path
import re
import shutil

from training_data import contained, digest, read_json, valid_box, vocabulary, write_json
from rfdetr_probe import ROOT, contract, decode_outputs, package_versions, utc


def mapped_raw(canonical):
    choices = [x for x in vocabulary() if x['canonical_id'] == canonical]
    # Map only an exact frozen canonical identity, never guess a similar category.
    choice = next((x for x in choices if x['name'] == 'Person'), choices[0] if choices else None)
    return choice['raw_id'] if choice else None


def validate_pack(pack, seed):
    if pack.get('schema') != 1 or pack.get('status') != 'completed' or pack.get('purpose') != 'rfdetr-annotation-proposals-only' or pack.get('approved_for_training') is not False:
        raise ValueError('RF catalogue is incomplete or not an unapproved proposal pack')
    if pack['source_manifest_sha256'] != seed['source_manifest_sha256'] or seed['classes'] != vocabulary():
        raise ValueError('RF catalogue belongs to another intake/vocabulary')
    if not re.fullmatch('[0-9a-f]{16}',pack['pack_id']) or not re.fullmatch('[0-9a-f]{64}',pack['model_sha256']):
        raise ValueError('Invalid RF catalogue/model identity')
    if pack['contract'] != contract() or pack['threshold'] != .35 or pack['backend'] != 'CPUExecutionProvider':
        raise ValueError('RF catalogue differs from the verified CPU/COCO contract')
    if not 1 <= len(pack['images']) <= 60 or len(pack['images']) != len(seed['images']):
        raise ValueError('RF catalogue must cover the exact bounded intake')
    coco = {x['raw_slot']:x for x in contract()['classes']}
    for row,image in zip(pack['images'],seed['images']):
        if (row['image_id'],row['sha256'],row['width'],row['height']) != (image['id'],image['sha256'],image['width'],image['height']):
            raise ValueError('RF photograph identity/geometry mismatch')
        if not isinstance(row['candidates'],list) or len(row['candidates']) > 300:
            raise ValueError('Invalid RF per-image prediction budget')
        for n,candidate in enumerate(row['candidates'],1):
            if set(candidate) != {'id','name','raw_slot','canonical_id','raw_id','box','confidence'}:
                raise ValueError('Unexpected RF candidate fields')
            raw_slot = candidate['raw_slot']
            if type(raw_slot) is not int or raw_slot not in coco:
                raise ValueError('Invalid sparse COCO slot')
            expected = coco[raw_slot]
            if type(candidate['canonical_id']) is not int or candidate['canonical_id'] != expected['canonical_id'] or candidate['name'] != expected['name']:
                raise ValueError('RF candidate class mapping changed')
            raw_id = candidate['raw_id']
            if (raw_id is not None and type(raw_id) is not int) or raw_id != mapped_raw(expected['canonical_id']):
                raise ValueError('RF candidate must use exact canonical mapping or an outside-vocabulary observation')
            if candidate['id'] != f"rf-{pack['pack_id']}-{image['id']}-{n}":
                raise ValueError('RF candidate identity changed')
            score = candidate['confidence']
            if type(score) not in (float,int) or not math.isfinite(score) or not .35 < score <= 1 or not valid_box(candidate['box'],image['width'],image['height']):
                raise ValueError('Invalid RF candidate confidence/geometry')
    return pack


def proposal_object(pack, image_id, candidate_id):
    if pack is None:
        raise ValueError('RF proposal history needs its original checked catalogue')
    row = next((x for x in pack['images'] if x['image_id'] == image_id),None)
    candidate = next((x for x in row['candidates'] if x['id'] == candidate_id),None) if row else None
    if candidate is None:
        raise ValueError('RF proposal does not exist in this photograph catalogue')
    outside = candidate['raw_id'] is None
    obj = {'id':('observation-' if outside else '')+candidate['id'],
           'box':copy.deepcopy(candidate['box']), 'status':'pending',
           'note':'RF-DETR suggestion: verify label, boundary, duplicates and missed objects.',
           'origin':{'kind':'model-observation' if outside else 'model','model':'RF-DETR Small',
                     'pack_id':pack['pack_id'],'candidate_id':candidate['id'],
                     'confidence':candidate['confidence'],'model_sha256':pack['model_sha256']}}
    obj['label' if outside else 'raw_id'] = candidate['name'] if outside else candidate['raw_id']
    return obj


def prepare_rf(workspace, annotations, experiment, output):
    from annotation_review import check_intake, load_checked, render_editor, summary, validate_state
    workspace,annotations,experiment = (Path(x).resolve(strict=True) for x in (workspace,annotations,experiment))
    output = Path(output).resolve()
    source,state = load_checked(workspace,annotations)
    if not 1 <= len(source['images']) <= 60:
        raise ValueError('RF annotation batch is capped at 60 existing photographs')
    if output.parent != workspace.parent or output == workspace or not output.is_relative_to(ROOT/'output'):
        raise ValueError('New RF workspace must be an output sibling of the existing workspace, keeping photograph links intact')
    if output.exists():
        raise FileExistsError('Existing RF workspace is preserved; choose a new output')
    seed = read_json(workspace/'seed.json')
    base_hash = digest(annotations)
    probe = read_json(experiment)
    if probe.get('status') != 'completed' or probe.get('sdk_and_onnx_cpu_parity_passed') is not True or probe.get('contract') != contract() or probe.get('source_manifest_sha256') != seed['source_manifest_sha256']:
        raise ValueError('Use the verified RF CPU export for this intake')
    if any(probe.get(x) is not False for x in ('approved_for_application','training_performed','accuracy_evaluated')):
        raise ValueError('This module only uses the unapproved pretrained mechanics export')
    model = Path(probe['export']['path']).resolve(strict=True)
    if not model.is_relative_to(experiment.parent) or digest(model) != probe['export']['sha256']:
        raise ValueError('Verified RF ONNX identity changed')
    versions = package_versions()
    import numpy as np
    import onnxruntime as ort
    import torch
    import torchvision.transforms.functional as transforms
    from PIL import Image
    torch.set_num_threads(4)
    options = ort.SessionOptions(); options.intra_op_num_threads = 4; options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
    if session.get_providers() != ['CPUExecutionProvider'] or [(x.name,x.shape,x.type) for x in session.get_inputs()] != [('input',[1,3,512,512],'tensor(float)')]:
        raise ValueError('RF session/input contract changed')
    if {x.name: (x.shape,x.type) for x in session.get_outputs()} != {'dets':([1,300,4],'tensor(float)'), 'labels':([1,300,91],'tensor(float)')}:
        raise ValueError('RF named output contract changed')
    meta = read_json(workspace/'workspace.json')
    if 'rfdetr_proposals' in meta:
        raise ValueError('This workspace already has RF suggestions. Render/resume its existing catalogue instead of replacing it.')
    manifest = Path(meta['source_manifest'])
    output.mkdir(parents=False,exist_ok=False)
    preparation = {'schema':1,'status':'running','purpose':'annotation-proposals-only','approved_for_training':False,
                   'started_at_utc':utc(),'base_annotations_sha256':base_hash,'source_workspace':str(workspace),
                   'probe_experiment_sha256':digest(experiment),'environment':versions,'images_completed':0}
    write_json(output/'preparation.json',preparation)
    pack_id = hashlib.sha256((seed['source_manifest_sha256']+probe['export']['sha256']+digest(Path(__file__))).encode()).hexdigest()[:16]
    pack = {'schema':1,'status':'running','purpose':'rfdetr-annotation-proposals-only','approved_for_training':False,
            'source_manifest_sha256':seed['source_manifest_sha256'],'pack_id':pack_id,'model_sha256':probe['export']['sha256'],
            'contract':contract(),'threshold':.35,'backend':'CPUExecutionProvider','images':[],
            'limits':'Unreviewed predictions, not accuracy or complete targets. Unmapped COCO classes are observations only. No automatic replacement or approval.'}
    try:
        for n,image in enumerate(source['images'],1):
            with Image.open(contained(manifest.parent,image['path'])) as decoded:
                tensor = transforms.to_tensor(decoded.convert('RGB'))
            tensor = transforms.resize(tensor,[512,512],antialias=False)
            tensor = transforms.normalize(tensor,pack['contract']['input']['mean'],pack['contract']['input']['std']).unsqueeze(0)
            boxes,logits = session.run(['dets','labels'],{'input':tensor.numpy()})
            predictions = decode_outputs({'dets':boxes,'labels':logits},image['width'],image['height'],threshold=.35)
            names = {x['canonical_id']:x['name'] for x in pack['contract']['classes']}
            candidates = [{'id':f"rf-{pack_id}-{image['id']}-{i}",'name':names[x['class_id']],
                           'raw_slot':x['raw_slot'],'canonical_id':x['class_id'],'raw_id':mapped_raw(x['class_id']),
                           'box':x['box'],'confidence':x['confidence']} for i,x in enumerate(predictions,1)]
            pack['images'].append({'image_id':image['id'],'sha256':image['sha256'],
                                  'width':image['width'],'height':image['height'],'candidates':candidates})
            write_json(output/'rf-proposals.json',pack)
            preparation['images_completed'] = n; write_json(output/'preparation.json',preparation)
            print(f"RF proposals {n}/{len(source['images'])}: {image['id']} — {len(candidates)} suggestions",flush=True)
        if digest(annotations) != base_hash or digest(model) != probe['export']['sha256']:
            raise ValueError('Base annotations or RF model changed during inference')
        check_intake(manifest)
        pack['status'] = 'completed';validate_pack(pack,seed)
        write_json(output/'rf-proposals.json',pack)
        shutil.copy2(workspace/'seed.json',output/'seed.json')
        write_json(output/'annotations.json',state)  # Exact prior state; RF proposals remain separate until human adoption.
        meta.update(created_at_utc=utc(),rfdetr_proposals={'path':'rf-proposals.json','sha256':digest(output/'rf-proposals.json')})
        write_json(output/'workspace.json',meta)
        render_editor(seed,state,output/'editor-rfdetr.html',pack)
        (output/'source-snapshot').mkdir()
        for filename in ('rfdetr_annotations.py','annotate-rfdetr.py','rfdetr_probe.py','annotation_review.py','annotation-editor.js','annotation-editor-simple.html'):
            shutil.copy2(ROOT/'scripts'/filename,output/'source-snapshot'/filename)
        preparation.update(status='completed',finished_at_utc=utc(),suggestions=sum(len(x['candidates']) for x in pack['images']),
                           outside_vocabulary_suggestions=sum(x['raw_id'] is None for row in pack['images'] for x in row['candidates']),
                           proposals_sha256=digest(output/'rf-proposals.json'),preserved_annotation_summary=summary(state))
        write_json(output/'preparation.json',preparation)
        return preparation
    except Exception as error:
        preparation.update(status='failed',finished_at_utc=utc(),error=str(error));write_json(output/'preparation.json',preparation)
        raise
