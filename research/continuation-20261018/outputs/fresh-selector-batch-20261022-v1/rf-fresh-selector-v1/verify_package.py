"""Pre-submission input verification. Does no inference/training/installations."""
import argparse,os,importlib.metadata
from pathlib import Path
from batch_guard import *

def verify(base,project=None,local_old=None,runtime=True):
    base=Path(base);verify_files(base);s=validate_scope(read(base/'SCOPE.json'))
    records=read(base/'INPUTS.json')['records'];schedules=[read(base/f'schedule-{seed}.json') for seed in s['seeds']]
    validate_inputs(records,schedules)
    for seed in s['seeds']:
        if sha(base/f'schedule-{seed}.json')!=s['schedule_sha256'][str(seed)]:raise ValueError('Schedule seal differs')
    from scoped_engine import validate_release,RF_SHA
    fresh=validate_release(base/'fresh/scoped-fresh-additions-v1.json')
    full=read(base/'receipts/fresh-full-manifest.json')
    if fresh['images']!=[r for r in full['images'] if r['split'] in ('train','val')]:raise ValueError('Fresh subset differs')
    if len(fresh['images'])!=92 or any(r['split']=='test' for r in fresh['images']):raise ValueError('Fresh TEST must stay local')
    old=Path(local_old) if local_old else Path(project)/'output/training-general-v1/rf-selector-a77d9663-v1'
    from release_guard import validate_draft
    old_manifest=old/'release/candidate-manifest-v2.json'
    validate_draft(old_manifest,OLD_RELEASE)
    old_rows={r['image_id']:r for r in read(old_manifest)['images']};fresh_rows={r['image_id']:r for r in fresh['images']}
    frozen={r['image_id']:r for r in read(base/'receipts/CPU_INPUTS.json')['records']}
    for r in records:
        if r['row']!=frozen[r['image_id']]['row'] or r['pool']!=frozen[r['image_id']]['pool']:raise ValueError('Paired-control input row changed')
        original=(fresh_rows if r['source']=='fresh' else old_rows)[r['image_id']]
        import copy
        row=copy.deepcopy(r['row'])
        if r['source']=='old':row.pop('scene_group',None)  # Frozen sampler-only grouping, checked exactly against CPU_INPUTS above.
        if r['source']=='fresh' or r['pool']!='old_absent':
            if row!=original:raise ValueError('Frozen row changed')
        else:
            modified=copy.deepcopy(original);modified['scope']['133']='absent'
            if row!=modified:raise ValueError('Whole-photo absent overlay changed more than reviewed scope')
    ck=old/'inputs/selected-7805570.pt'
    if sha(ck)!=CHECKPOINT:raise ValueError('Starting checkpoint differs')
    if runtime:
        import torch
        if str(torch.__version__)!='2.8.0+cu128' or torch.version.cuda!='12.8' or importlib.metadata.version('rfdetr')!='1.11.2':raise ValueError('Pinned KIT runtime differs; no installation')
        weights=Path(project)/'output/rf-comparison-v1/assets/rf-detr-small.pth'
        if sha(weights)!=RF_SHA:raise ValueError('Original RF weights changed')
    return dict(status='package-scope-data-checkpoint-verified',scope_sha256=sha(base/'SCOPE.json'),train_photos=124,
      validation_photos_local=167,remaining_gpu_tasks=2,remaining_updates=3000,training=False,inference=False,test_photos_used=0)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);a=ap.parse_args()
    print(__import__('json').dumps(verify(Path(__file__).parent,a.project)))
