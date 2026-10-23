"""Frozen current-model baseline/cache on fresh TRAIN+validation only; never fresh test inference."""
import os,sys,json,time,hashlib,importlib.metadata
from pathlib import Path
R=Path(__file__).resolve().parent;OUT=R.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
F=OUT/'frozen-head-cpu-7809335-20261018-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(F),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1')
import torch
from scoped_engine import build_model,load_sample,validate_release
from scoped_metrics import decode,score
from determinism_policy import math_attention
from cache_engine import capture,replay,max_output_error
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
@math_attention()
def main():
 assert str(torch.__version__)=='2.8.0+cpu' and importlib.metadata.version('rfdetr')=='1.11.2'
 assert read(R/'READINESS_REPORT.json')['ready_for_package_preparation']
 release_path=R/'reviewed-release-v1/scoped-fresh-additions-v1.json'
 release=validate_release(release_path)
 rows=[r for r in release['images'] if r['split'] in ('train','val')]
 assert len(rows)==92 and len([r for r in rows if r['split']=='val'])==32
 B=OUT/'fresh-data-baseline-20261021-v1';B.mkdir(exist_ok=False);(B/'cache').mkdir()
 checkpoint=T/'inputs/selected-7805570.pt'
 expected='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3';assert sha(checkpoint)==expected
 torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
 start=time.monotonic()
 write(B/'BASELINE_SCOPE.json',dict(status='started',checkpoint_sha256=expected,release_sha256=sha(release_path),
   input_roles=['train','val'],train_photos=60,validation_photos=32,test_photos_used=0,
   threshold=.35,nms_iou=.45,match_iou=.5,global_topk=300,max_detections=100,
   validation_selection=False,training=False,threads=2,torch=str(torch.__version__),rfdetr=importlib.metadata.version('rfdetr')))
 model=build_model(Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth'),T/'rf-mapping.json').cpu().eval()
 state=torch.load(checkpoint,map_location='cpu',weights_only=True);model.load_state_dict(state['model_state_dict'],strict=True);del state
 for p in model.parameters():p.requires_grad_(False)
 predictions={};cache_index=[];errors=[]
 with torch.inference_mode():
  for n,row in enumerate(rows,1):
   assert row['split']!='test'
   image,target=load_sample(release_path.parent,row,'cpu')
   cache,outputs=capture(model,image,full=True)
   replayed=replay(cache,model.class_embed.weight,model.class_embed.bias)
   err=max_output_error(outputs,replayed);assert err==0,(row['image_id'],err)
   pred=decode(outputs,row['width'],row['height'])
   if row['split']=='val':predictions[row['image_id']]=pred
   path=B/'cache'/(row['image_id']+'.pt')
   torch.save(dict(cache=cache,target=target,image_id=row['image_id'],split=row['split'],image_sha256=row['image_sha256'],checkpoint_sha256=expected),path)
   cache_index.append(dict(image_id=row['image_id'],split=row['split'],sha256=sha(path),path=str(path),features_shape=list(cache['features'].shape),max_replay_output_error=err))
   if n%8==0:print(json.dumps(dict(completed=n,total=len(rows),elapsed_seconds=round(time.monotonic()-start,1))),flush=True)
 val=[r for r in rows if r['split']=='val'];metrics=score(val,predictions)
 write(B/'validation-predictions.json',predictions);write(B/'CACHE_INDEX.json',dict(checkpoint_sha256=expected,release_sha256=sha(release_path),records=cache_index,test_photos_used=0,training=False))
 viable=metrics['complete_fn']>=3
 report=dict(status='frozen-fresh-validation-baseline-completed',checkpoint_sha256=expected,release_sha256=sha(release_path),metrics=metrics,
   planned_three_hit_gain_is_mathematically_possible=viable,baseline_missed_targets=metrics['complete_fn'],
   no_threshold_or_dataset_changes_after_scores=True,test_photos_used=0,training=False,production_adoption=False,
   exact_full_layout_replay_passed=len(cache_index),elapsed_seconds=round(time.monotonic()-start,2),
   next_action='Prepare exact-layout loss/gradient checks and paired CPU controls before two-GPU selector batch' if viable else 'Do not launch the frozen gain experiment or swap validation photos; investigate a new prospectively frozen question')
 write(B/'BASELINE_REPORT.json',report);print(json.dumps(report),flush=True)
 assert sha(checkpoint)==expected
if __name__=='__main__':main()

