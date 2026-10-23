"""Actual sealed-package verification and real model patch roundtrip, with no fit or TEST inference."""
import sys,os,time,importlib.metadata,ast
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;BASE=HERE/'rf-fresh-selector-v1'
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(BASE),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1')
import torch
from batch_guard import *
from verify_package import verify
from scoped_engine import build_model,load_sample
from scoped_metrics import decode
from selector_mechanics import configure,capture_dense,dense_billboard_loss
from scoped_rf import ScopedRFCriterion,weighted_loss
from determinism_policy import math_attention,backward

@math_attention()
def main():
    started=time.monotonic();receipt=read(HERE/'archive-receipt.json')
    assert sha(HERE/receipt['archive'])==receipt['archive_sha256']
    assert sha(BASE/'package-files.json')==receipt['package_seal_sha256']
    report=verify(BASE,local_old=T,runtime=False)
    for p in list(BASE.glob('*.py'))+[HERE/'local_followup.py',HERE/'build_package.py']:
        ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    import tarfile
    with tarfile.open(HERE/receipt['archive'],'r:gz') as tf:
        names=tf.getnames();assert len(names)==len(set(names))==499
        test_ids={r['image_id'] for r in read(BASE/'receipts/fresh-full-manifest.json')['images'] if r['split']=='test'}
        assert not any(any(i+'.jpg' in name for i in test_ids) for name in names)
        assert all(not m.issym() and not m.islnk() for m in tf.getmembers())
    assert str(torch.__version__)=='2.8.0+cpu' and importlib.metadata.version('rfdetr')=='1.11.2'
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    model=build_model(Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth'),BASE/'rf-mapping.json').cpu().eval()
    value=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(value['model_state_dict'],strict=True);del value
    before=frozen_digest(model.state_dict());meta=dict(scope_sha256=receipt['scope_sha256'],seed=17,step=0,starting_checkpoint_sha256=CHECKPOINT,actual_job_id='123_0')
    patch=make_patch(model.state_dict(),meta);check_patch(patch,receipt['scope_sha256'],17,0,'123_0')
    original_rows={k:v.clone() for k,v in patch['rows'].items()}
    for k in patch['rows']:patch['rows'][k].add_(.0001)
    apply_patch_rows(model,patch);assert frozen_digest(model.state_dict())==before
    assert all(tensor_digest(model.state_dict()[k][133])==tensor_digest(v) for k,v in patch['rows'].items())
    apply_patch_rows(model,dict(rows=original_rows));assert frozen_digest(model.state_dict())==before
    # Exercise actual new-package loader, exact scoped loss, dense objective and hooks without optimizer.step.
    optimizer,check,allowed=configure(model,.00003,.0001);records={r['image_id']:r for r in read(BASE/'INPUTS.json')['records']}
    fixtures=read(BASE/'schedule-17.json')[0];results=[]
    baseline=read(OUT/'fresh-data-baseline-20261021-v1/validation-predictions.json')
    val_record=next(r for r in records.values() if r['pool']=='fresh_validation')
    with torch.inference_mode():
        x,_=load_sample(BASE/'fresh',val_record['row'],'cpu');pred=decode(model(x),val_record['row']['width'],val_record['row']['height'])
        assert pred==baseline[val_record['image_id']]
    for iid in fixtures:
        r=records[iid];root=BASE/'fresh' if r['source']=='fresh' else T/'release';x,target=load_sample(root,r['row'],'cpu')
        optimizer.zero_grad(set_to_none=True);outputs,raw=capture_dense(model,x);dense=dense_billboard_loss(raw,target,None,1.)
        loss=(weighted_loss(ScopedRFCriterion(615)(outputs,[target]))+dense)/4;backward(loss)
        for name,p in model.named_parameters():
            if name not in allowed:assert p.grad is None
            else:assert p.grad is not None and not bool(p.grad[[i for i in range(616) if i!=133]].any())
        check();assert frozen_digest(model.state_dict())==before
        results.append(dict(image_id=iid,pool=r['pool'],loss=float(loss.detach()),dense_loss=float(dense.detach()),gradient_scope_passed=True))
    write(HERE/'BUILT_PACKAGE_CHECK.json',dict(status='passed',package_verification=report,python_syntax_passed=True,archive_members=499,
      TEST_pixels_absent=True,real_model_patch_roundtrip_passed=True,all_frozen_and_inactive_bytes_unchanged=True,actual_forward_loss_gradient_fixtures=results,
      current_reference_prediction_equal=True,optimizer_updates=0,test_inference_photos=0,cluster_jobs_submitted=0,elapsed_seconds=time.monotonic()-started,package_seal_sha256=receipt['package_seal_sha256']))
    print(json.dumps(read(HERE/'BUILT_PACKAGE_CHECK.json'),indent=2))
if __name__=='__main__':main()
