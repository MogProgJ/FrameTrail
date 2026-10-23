"""Pinned runtime, original model and starting checkpoint metadata; no inference."""
import argparse,importlib.metadata,json
from pathlib import Path
from continuation_guard import approval,sha,read
T=Path(__file__).resolve().parent
def preflight(project,local_cpu=False,preparation_only=False):
    p=read(T/'protocol.json') if preparation_only else approval(T)[1];runtime=read(T/'runtime-lock.json');import torch
    expected='2.8.0+cpu' if local_cpu else runtime['torch_version']
    if str(torch.__version__)!=expected or (not local_cpu and torch.version.cuda!=runtime['CUDA']) or importlib.metadata.version('rfdetr')!=runtime['rfdetr']:raise ValueError('Pinned runtime differs; no automatic installation')
    weights=project/'.deps/rfdetr-probe-assets/rf-detr-small.pth' if local_cpu else project/'output/rf-comparison-v1/assets/rf-detr-small.pth'
    if sha(weights)!='d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33':raise ValueError('Original pretrained model changed or missing')
    ckpt=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)
    if ckpt['step']!=100 or ckpt['frametrail']['actual_job_id']!='7805570' or ckpt['approved_for_application'] is not False or ckpt['model_state_dict']['class_embed.weight'].shape[0]!=616:raise ValueError('Wrong checkpoint provenance or dimensions')
    return dict(status='local-CPU-preflight-passed-no-GPU-submission' if local_cpu else 'KIT-runtime-and-input-preflight-passed',local_cpu=local_cpu,GPU_inference=False,training=False,weights_sha256=sha(weights),starting_checkpoint_sha256=p['starting_checkpoint']['sha256'])
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--local-cpu',action='store_true');ap.add_argument('--preparation-only',action='store_true');a=ap.parse_args();
    if a.preparation_only and not a.local_cpu:raise ValueError('Preparation bypass is local CPU metadata inspection only')
    print(json.dumps(preflight(a.project,a.local_cpu,a.preparation_only)))
