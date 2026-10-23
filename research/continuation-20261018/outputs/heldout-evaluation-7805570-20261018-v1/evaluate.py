"""Frozen CPU evaluation only: no optimizer, reselection, export or adoption."""
import argparse, copy, gc, hashlib, importlib.metadata, json, os, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUTROOT=HERE.parent
ART=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\17\01a14c2d-b771-7a40-ba9b-e8277e4905a1')
PREVIOUS=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
OLDER=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb')
TOOLS=ART/'work/rf-balanced-continuation-20261018-v1/rf-balanced-ddbb57c6-v1'
AUDITED=OUTROOT/'rf-balanced-verification-repair-7805570-20261018-v1'
sys.dont_write_bytecode=True
sys.path[:0]=[str(TOOLS),str(OLDER),str(OLDER/'rf-comparison-package-20261013-v1/local-assignment-wheel/torch_hungarian-0.1.0rc0-py3-none-any.whl')]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',MPLCONFIGDIR=str(HERE/'runtime-cache/matplotlib'))
import torch
from PIL import Image
from torchvision.transforms import functional as TF
from scoped_engine import build_model
from scoped_metrics import decode
from determinism_policy import math_attention
import score_video_reference as scorer

CHECKPOINTS={
 'original_baseline':dict(path=str(OUTROOT/'trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632/best.pt'),sha256='3a9adf74b11b851fba7393cc41b12b538a7aa1576b0a4e179468cc36c2279389',step=0),
 'continuation_baseline':dict(path=str(TOOLS/'inputs/last-7780632.pt'),sha256='d280723323b4ae8b07f1631667f2d87a9744c3398a06cc94e71dcef04fae2a02',step=600),
 'candidate':dict(path=str(AUDITED/'verified-7805570/output/rf-balanced-7805570/best.pt'),sha256='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',step=100)}
SOURCES={
 'heldout_photos':TOOLS/'release/candidate-manifest-v2.json',
 'reserved_video':PREVIOUS/'nextdata-fresh-reference-7769109-v1/scoped-reference.json',
 'internal_regression':OLDER/'rf-evaluation-7696017-20261014-v1/internal_test-reference.json',
 'old_video':OLDER/'rf-evaluation-7696017-20261014-v1/known_video_regression-reference.json',
 'recent_video':OLDER/'rf-fresh-video-20261014-v1/scoped-reference.json',
 'scale_video':PREVIOUS/'rf-scale-fresh-video-7752340-v1/scoped-reference.json'}
PINNED={
 'heldout_photos':'e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9',
 'reserved_video':'3d3f0c6c932bf10a444b78bfce6b3b33261af8060bfedc28cf89a4c636c27762',
 'internal_regression':'d5e4fc4b32536d382ab284afd88671b9e9e5f64811372c50727c0b0851e87110',
 'old_video':'cd80c08b08b32ed6a5cc66ff1d1dc41aaca41dc6605948b7ac00ac2f2788cc41',
 'recent_video':'eee323c6925ba9502d2735b324ff0d9be5d04ff0f6e62528e3721dd78d701b9c',
 'scale_video':'4f7cd45b48eb47cba9c5ab6650d7841ae4fc4071dc59a388ff6a9fdff069531c'}
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
THRESHOLDS=dict(confidence=.35,nms_iou=.45,match_iou=.5,max_detections=100,top_pairs=300,input_size=512)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if read(p)!=value:raise ValueError('Existing artifact differs: '+str(p))
    else:
        with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False)
def fingerprint(state):
    d=hashlib.sha256()
    for k,v in sorted(state.items()):
        d.update(k.encode());d.update(str(v.dtype).encode());d.update(str(tuple(v.shape)).encode());d.update(v.detach().cpu().contiguous().numpy().tobytes())
    return d.hexdigest()

def photo_frame(row,names,base):
    w,h=row['width'],row['height'];targets=[]
    for i,t in enumerate(row['targets']):
        cx,cy,bw,bh=t['normalized_cxcywh'];cid=t['canonical_id']
        targets.append(dict(id=f'{row["image_id"]}-{i}',canonical_id=cid,label=names[cid],
            box=[(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h]))
    return dict(id=row['image_id'],sequence=row['identity_group'],width=w,height=h,targets=targets,
        path=str(base/row['source_path']),sha256=row['image_sha256'],original_split='test',
        complete_class_scopes=[dict(canonical_id=int(k),complete=True,absence_confirmed=v=='absent')
            for k,v in row['scope'].items() if v in ('complete','absent')])

def normalized_reference(label,source,names,vocab):
    if label=='heldout_photos':
        rows=[r for r in source['images'] if r['split']=='test'];assert len(rows)==130
        frames=[photo_frame(r,names,SOURCES[label].parent) for r in rows]
    else:frames=copy.deepcopy(source['frames'])
    # Add scorer metadata without modifying any original source or annotation.
    return dict(purpose='frozen-scoped-evaluation-adapter',source_sha256=PINNED[label],frames=frames,
        vocabulary=vocab,vocabulary_sha256=hashlib.sha256(json.dumps(vocab,sort_keys=True).encode()).hexdigest(),
        baseline_identity=dict(confidence=.35,nms_iou=.45,max_detections=100),evaluation=dict(iou_threshold=.5),
        approved_for_training=False,frozen_label_and_metric_scope=True)

def score_predictions(ref,predictions,identity):
    payload=dict(reference_sha256=ref['source_sha256'],class_namespace='native-canonical',
        vocabulary_sha256=ref['vocabulary_sha256'],confidence_threshold=.35,identity=identity,
        frames=[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']])
    result=scorer.score(ref,payload,ref['source_sha256'])
    result['limits']='Scoped evaluation at confidence .35, class-wise NMS .45, match IoU .5. Partial labels support known-positive recall only; unmatched unknown predictions are unscored. Small assistant-reviewed evidence, not full-vocabulary AP, tracking performance, or independent representative accuracy.'
    return payload,result

def gate(b,c):
    zero=dict(complete_tp=0,complete_fp=0,partial_positive_hits=0)
    checks=[]
    for name in sorted(set(b['by_class'])|set(c['by_class'])):
        before=b['by_class'].get(name,zero);after=c['by_class'].get(name,zero)
        for key,op in [('complete_tp','at-least'),('partial_positive_hits','at-least'),('complete_fp','at-most')]:
            passed=after[key]>=before[key] if op=='at-least' else after[key]<=before[key]
            if not passed:checks.append(dict(category=name,metric=key,baseline=before[key],candidate=after[key]))
    return dict(passed=not checks,failures=checks)

def prepare():
    if (HERE/'evaluation-lock.json').exists():raise ValueError('Lock already exists; use --run to resume with identity checks')
    audit=read(AUDITED/'AUDIT.json');assert audit['selected_step']==100 and audit['selection_recomputed']
    assert audit['selected_checkpoint_sha256']==CHECKPOINTS['candidate']['sha256']
    protocol=read(TOOLS/'protocol.json')
    assert sha(TOOLS/'protocol.json')=='ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1'
    assert protocol['evaluation']['fresh_reference_sha256']==PINNED['reserved_video']
    assert str(torch.__version__)=='2.8.0+cpu' and importlib.metadata.version('rfdetr')=='1.11.2'
    assert sha(WEIGHTS)=='d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33'
    assert sha(TOOLS/'rf-mapping.json')=='fe743b7b4182cffc190486ad9dbb576afb4610fb37e1db67b0f93dc4fec02524'
    mapping=read(TOOLS/'rf-mapping.json')['canonical_class_names']
    names=[mapping[str(i)] for i in range(615)] if isinstance(mapping,dict) else mapping
    vocab=[dict(canonical_id=i,canonical_name=name) for i,name in enumerate(names)]
    manifest=read(SOURCES['heldout_photos']);train={r['image_sha256'] for r in manifest['images'] if r['split']=='train'}
    train_groups={r['identity_group'] for r in manifest['images'] if r['split']=='train'}
    sources={};images={}
    for label,path in SOURCES.items():
        assert sha(path)==PINNED[label]
        source=read(path);ref=normalized_reference(label,source,names,vocab)
        if label=='reserved_video':
            assert len(ref['frames'])==24 and len({f['sequence'] for f in ref['frames']})==6
        for f in ref['frames']:
            assert f['sha256'] not in train and f['sequence'] not in train_groups
            assert sha(f['path'])==f['sha256']
            with Image.open(f['path']) as im:assert im.size==(f['width'],f['height']) and im.getexif().get(274,1)==1
            if f['sha256'] in images:assert (images[f['sha256']]['width'],images[f['sha256']]['height'])==(f['width'],f['height'])
            else:images[f['sha256']]=dict(path=f['path'],width=f['width'],height=f['height'])
        save(HERE/'references'/f'{label}.json',ref)
        sources[label]=dict(path=str(path),sha256=sha(path),adapter_sha256=sha(HERE/'references'/f'{label}.json'),frames=len(ref['frames']),targets=sum(len(f['targets']) for f in ref['frames']))
    for ck in CHECKPOINTS.values():assert sha(ck['path'])==ck['sha256']
    preservation_paths=list(SOURCES.values())+[Path(c['path']) for c in CHECKPOINTS.values()]+[WEIGHTS,TOOLS/'protocol.json',TOOLS/'approval.json',AUDITED/'AUDIT.json',PREVIOUS/'nextdata-fresh-reference-7769109-v1/reference-lock.json']
    preservation_paths += [Path(d['path']) for d in images.values()]
    files={str(p):sha(p) for p in dict.fromkeys(preservation_paths)}
    modules={str(p):sha(p) for p in [Path(__file__),Path(scorer.__file__),TOOLS/'scoped_engine.py',TOOLS/'scoped_metrics.py',TOOLS/'determinism_policy.py',TOOLS/'scoped_rf.py',TOOLS/'rf-mapping.json']}
    lock=dict(job='7805570',selected_step=100,checkpoints=CHECKPOINTS,references=sources,images=images,
        thresholds=THRESHOLDS,torch_version=str(torch.__version__),rfdetr_version=importlib.metadata.version('rfdetr'),
        backend='PyTorchCPU/FP32/math-attention',cpu_threads=2,seed=17,
        adoption_gate='For every reference and reviewed class, preserve complete TP and partial known-positive hits and do not increase complete FP, against BOTH pinned baselines. Require a strict total known-positive gain on heldout_photos plus reserved_video against BOTH. No automatic app adoption.',
        useful_gain_sets=['heldout_photos','reserved_video'],scoring_modules=modules,input_hashes=files,
        unique_images=len(images),maximum_full_forward_calls=len(images)*3,
        no_checkpoint_or_threshold_reselection=True,no_training=True,automatic_GPU_jobs=0,approved_for_application=False,
        authorization='User: Okay, then proceed to the next step. Keep working until my input is required. Frozen held-out evaluation recommended immediately before authorization.')
    save(HERE/'evaluation-lock.json',lock)
    print(json.dumps({'status':'frozen-before-inference','unique_images':len(images),'maximum_forward_calls':len(images)*3,'references':sources},indent=2),flush=True)

@math_attention()
def run():
    lock=read(HERE/'evaluation-lock.json');locksha=sha(HERE/'evaluation-lock.json')
    assert lock['checkpoints']==CHECKPOINTS and lock['thresholds']==THRESHOLDS
    for p,h in lock['scoring_modules'].items():assert sha(p)==h
    for p,h in lock['input_hashes'].items():assert sha(p)==h
    assert str(torch.__version__)==lock['torch_version'] and importlib.metadata.version('rfdetr')==lock['rfdetr_version']
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    model=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval()
    for p in model.parameters():p.requires_grad_(False)
    results={};state_checks={};calls={};total_started=time.perf_counter()
    for role,ck in CHECKPOINTS.items():
        loaded=torch.load(ck['path'],map_location='cpu',weights_only=True)
        assert loaded['step']==ck['step'] and loaded['approved_for_application'] is False
        model.load_state_dict(loaded['model_state_dict'],strict=True);del loaded;gc.collect()
        model.eval();before=fingerprint(model.state_dict());pred={};calls[role]=0
        identity=dict(role=role,checkpoint_sha256=ck['sha256'],evaluation_lock_sha256=locksha,backend=lock['backend'])
        for number,(digest,image) in enumerate(lock['images'].items(),1):
            target=HERE/role/'images'/f'{digest}.json'
            if target.exists():
                record=read(target);assert record['identity']==identity and record['image_sha256']==digest
            else:
                with Image.open(image['path']) as im:
                    x=TF.normalize(TF.resize(TF.to_tensor(im.convert('RGB')),[512,512],antialias=False),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0)
                started=time.perf_counter()
                with torch.inference_mode():outputs=model(x)
                detections=decode(outputs,image['width'],image['height'])
                record=dict(identity=identity,image_sha256=digest,detections=detections,seconds=time.perf_counter()-started)
                save(target,record);calls[role]+=1
            pred[digest]=record['detections']
            if number%10==0 or number==len(lock['images']):print(f'{role}: {number}/{len(lock["images"])} images; elapsed {time.perf_counter()-total_started:.1f}s',flush=True)
        after=fingerprint(model.state_dict());assert before==after
        state_checks[role]=dict(before=before,after=after,unchanged=True)
        results[role]={}
        for label,source in lock['references'].items():
            p=HERE/'references'/f'{label}.json';assert sha(p)==source['adapter_sha256']
            payload,result=score_predictions(read(p),pred,identity)
            save(HERE/role/label/'predictions.json',payload);save(HERE/role/label/'scoped-results.json',result)
            results[role][label]=result
            print(role,label,json.dumps(result['aggregate']),flush=True)
    retention={};gain={}
    hits=lambda r:r['aggregate']['complete_tp']+r['aggregate']['partial_positive_hits']
    for baseline in ['original_baseline','continuation_baseline']:
        retention[baseline]={label:gate(results[baseline][label],results['candidate'][label]) for label in lock['references']}
        before=sum(hits(results[baseline][k]) for k in lock['useful_gain_sets'])
        after=sum(hits(results['candidate'][k]) for k in lock['useful_gain_sets'])
        gain[baseline]=dict(baseline=before,candidate=after,strict_gain=after>before)
    passed=all(g['passed'] for b in retention.values() for g in b.values()) and all(g['strict_gain'] for g in gain.values())
    for p,h in lock['input_hashes'].items():assert sha(p)==h
    comparison=dict(status='frozen-heldout-evaluation-complete',job='7805570',selected_step=100,
        selected_checkpoint_sha256=CHECKPOINTS['candidate']['sha256'],evaluation_lock_sha256=locksha,
        metrics={role:{label:r['aggregate'] for label,r in sets.items()} for role,sets in results.items()},
        retention_gates=retention,heldout_strict_gain=gain,evidence_gate_passed=passed,
        decision='eligible-for-separate-export-parity-and-performance-gates' if passed else 'hold-no-export-or-adoption',
        parameter_state_checks=state_checks,new_forward_calls=calls,total_forward_records=len(lock['images'])*3,
        all_inputs_unchanged=True,heldout_now_consumed_as_regression_evidence=True,
        training_updates=0,new_GPU_jobs=0,model_exported=False,approved_for_application=False,
        limits='Small purposive assistant-reviewed sets. Partial labels do not measure precision. Known regression sets are not fresh evidence. No representative accuracy, statistical significance, source/pretraining independence or tracking accuracy claim.')
    save(HERE/'comparison.json',comparison)
    print(json.dumps({k:comparison[k] for k in ['status','decision','retention_gates','heldout_strict_gain','new_forward_calls']},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.prepare==a.run:raise SystemExit('Choose exactly one: --prepare or --run')
    prepare() if a.prepare else run()
