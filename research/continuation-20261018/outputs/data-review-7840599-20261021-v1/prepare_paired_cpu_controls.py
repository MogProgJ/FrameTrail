"""Seal TRAIN-only paired schedules from predeclared19Oct rules. No fitting or cluster submission."""
import json,hashlib,random,copy,sys
from pathlib import Path
from collections import defaultdict,Counter
OUT=Path(__file__).resolve().parent.parent
D=OUT/'data-review-7840599-20261021-v1';F=OUT/'frozen-head-cpu-7809335-20261018-v1'
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
OLD=OUT/'selector-diagnosis-7818553-20261018-v1';B=OUT/'fresh-data-baseline-20261021-v1'
C=OUT/'fresh-paired-controls-20261021-v1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(p.resolve()),sha256=sha(p))
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
sys.path.insert(0,str(T));from release_guard import validate_draft
original_path=T/'release/candidate-manifest-v2.json'
original=validate_draft(original_path,'e43a2c7a415c4f82209a1fc2471d8677503f51315e71f422ec0d6665eac377b9')
fresh_path=D/'reviewed-release-v1/scoped-fresh-additions-v1.json';fresh=read(fresh_path)
assert sha(fresh_path)=='b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09'
assert read(D/'READINESS_REPORT.json')['ready_for_package_preparation']
old_rows={r['image_id']:r for r in original['images']}
held={r['image_id'] for r in read(OLD/'TRAIN_POSITIVE_REVIEW.json')['records'] if r['disposition']=='category_boundary_hold'}
pools_old=read(T/'sampling-pools.json')
pos=sorted(set(pools_old['billboard'])-held);assert len(pos)==17
overlay={r['image_id']:r for r in read(OLD/'TRAIN_CONTRAST_OVERLAY.json')['records'] if r['supervision']=='whole_photo_billboard_absent'}
neg=sorted(set(pools_old['explicit_negative'])|set(overlay));assert len(neg)==47
old_index=read(F/'CACHE_INDEX_FULL_LAYOUT.json')
extra={r['image_id']:r for r in read(OLD/'local-contrast/CACHE_RECEIPT.json')['records']}
fresh_index={r['image_id']:r for r in read(B/'CACHE_INDEX.json')['records']}
# Known recurring Times Square venue; merge across photographers conservatively.
times_square={'c310febc40974a94','867a012fafb5766c','995211dda562c920','88ced829147507c7','89f3b4db87857c8d'}
records=[];pools={k:[] for k in ('fresh_positive','old_positive','fresh_absent','old_absent')}
for iid in pos+neg+[r['image_id'] for r in original['images'] if r['split']=='val']:
 row=copy.deepcopy(old_rows[iid]);kind='old_positive' if iid in pos else 'old_absent' if iid in neg else 'old_validation'
 if kind=='old_absent' and iid in overlay:
  assert row['scope'].get('133','unknown')=='unknown' and not any(t['canonical_id']==133 for t in row['targets'])
  row['scope']['133']='absent'
 row['scene_group']='old-times-square' if iid in times_square else 'old-owner-conservative:'+row['identity_group']
 if iid in old_index:
  p=F/'cache-full-layout'/(iid+'.pt');expected=old_index[iid]['cache_sha256'];assert old_index[iid]['split']==row['split']
 else:
  assert kind=='old_absent' and iid in extra;p=OLD/'local-contrast/cache'/(iid+'.pt');expected=extra[iid]['cache_sha256']
 assert sha(p)==expected
 rec=dict(image_id=iid,pool=kind,row=row,cache_ref=ref(p),base=str(original_path.parent),source='old-protected-release')
 records.append(rec)
 if kind in pools:
  assert row['split']=='train';pools[kind].append(iid)
for row in fresh['images']:
 if row['split']=='test':continue
 iid=row['image_id'];kind='fresh_positive' if row['targets'] else 'fresh_absent'
 if row['split']=='val':kind='fresh_validation'
 index=fresh_index[iid];assert index['split']==row['split'] and sha(index['path'])==index['sha256']
 records.append(dict(image_id=iid,pool=kind,row=row,cache_ref=index if False else dict(path=index['path'],sha256=index['sha256']),base=str(fresh_path.parent),source='fresh-reviewed-release'))
 if kind in pools:
  assert row['split']=='train';pools[kind].append(iid)
byid={r['image_id']:r for r in records};assert len(byid)==len(records)==291
def cycle(ids,seed,slot):
 groups=defaultdict(list)
 for iid in sorted(ids):groups[byid[iid]['row']['scene_group']].append(iid)
 rng=random.Random(seed*100+slot);within={g:random.Random(int(hashlib.sha256((str(seed)+':'+str(slot)+':'+g).encode()).hexdigest()[:16],16)) for g in groups}
 queues={g:[] for g in groups};out=[]
 while len(out)<1500:
  order=sorted(groups);rng.shuffle(order)
  for g in order:
   if not queues[g]:
    queues[g]=sorted(groups[g]);within[g].shuffle(queues[g])
   out.append(queues[g].pop())
   if len(out)==1500:break
 return out
C.mkdir(exist_ok=False)
schedule_refs=[]
for seed in (17,29):
 streams=[cycle(pools[k],seed,j) for j,k in enumerate(pools)]
 schedule=[list(v) for v in zip(*streams)]
 assert len(schedule)==1500 and all(len(set(b))==4 and all(byid[i]['row']['split']=='train' for i in b) for b in schedule)
 p=C/('schedule-'+str(seed)+'.json');write(p,schedule);schedule_refs.append(dict(seed=seed,**ref(p)))
write(C/'INPUTS.json',dict(records=records,pools=pools,old_manifest_ref=ref(original_path),fresh_manifest_ref=ref(fresh_path),old_positive_review_ref=ref(OLD/'TRAIN_POSITIVE_REVIEW.json'),old_absent_overlay_ref=ref(OLD/'TRAIN_CONTRAST_OVERLAY.json'),initial_head_ref=ref(F/'cache-full-layout/initial-head.pt'),old_original_baseline_ref=ref(T/'inputs/validation-original.json'),old_current_baseline_ref=ref(T/'inputs/validation-resume.json')))
write(C/'EXECUTION_ORDER_NOTE.json',dict(status='transparent-ordering-deviation-before-any-fitting',
 earlier_design_ref=ref(OUT/'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json'),
 exact_schedule_files_sealed_before_baseline_predictions=False,exact_schedule_files_sealed_before_fitting=True,
 prebaseline_rules='Seeds17/29, four ordered TRAIN pools, scene-fair cycling,1500updates and optimizer/validation thresholds were specified19Oct.',
 actual_order='Reviewed124-photo label release frozen; current baseline measured; exact sampler now materialized. No fits or candidate predictions have run.',
 safeguard='Sampler implementation consumes only fixed TRAIN pools,scene groups and predeclared seeds. No validation/test rows, predictions or performance values enter cycle(). No pool/hyperparameter/threshold choices changed in response to0/14.',
 limits='Do not claim literal exact-schedule-before-predictions compliance or fully preregistered implementation. Retain this deviation in every experiment report. Source/split/retention/gain/locked-test gates unchanged.',
 authority='Standing18Oct autonomous local preparation/reviews/fixes; this note does not authorize resource expansion or erase original design.'))
plan=dict(status='sealed-local-control-plan-pending-loss-gradient-preflight',starting_checkpoint_sha256='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',
 input_ref=ref(C/'INPUTS.json'),schedule_refs=schedule_refs,execution_order_note_ref=ref(C/'EXECUTION_ORDER_NOTE.json'),
 baseline_ref=ref(B/'BASELINE_REPORT.json'),strategy_ref=ref(OUT/'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json'),
 method='M0-main-row133-only',main_lr=.0001,weight_decay=0,clip=.1,AMP=False,threads=2,
 max_updates=1500,active_seconds_per_control=1800,finalization_seconds=480,sequential=True,validation_steps=[0,100,250,500,1000,1500],
 loss='Unchanged scoped Hungarian IA-BCE/box/aux criterion averaged over four photos. Frozen encoder dense objective has zero active-main gradient; constant term omitted from M0 optimization loss only, explicitly reported.',
 selection='freshval gain>=3hits with0extraFP;old perclass bothbaselines;original unknown cap530;bothseeds required. No TESTinference or model adoption.',
 scene_grouping='Fresh124 explicit scene adjudications. Replay: existing photographer groups conservatively merged, plus known five Times Square TRAIN photos merged across owners. No validation/test exposure in TRAIN pools.')
write(C/'PLAN.json',plan)
print(json.dumps(dict(input_records=len(records),train_pools={k:len(v) for k,v in pools.items()},schedules=schedule_refs,plan_ref=ref(C/'PLAN.json'))))

