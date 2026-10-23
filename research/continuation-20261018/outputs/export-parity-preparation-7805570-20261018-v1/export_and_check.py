"""Prepared separate local export/parity stage. Execute only after scope approval."""
import copy,hashlib,importlib.metadata,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;EVAL=HERE.parent/'heldout-evaluation-7805570-20261018-v1'
TOOLS=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\17\01a14c2d-b771-7a40-ba9b-e8277e4905a1\work\rf-balanced-continuation-20261018-v1\rf-balanced-ddbb57c6-v1')
sys.dont_write_bytecode=True
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(TOOLS),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',MPLCONFIGDIR=str(HERE/'runtime-cache/matplotlib'))
import numpy as np,torch,onnx,onnxruntime as ort
from PIL import Image
from torchvision.transforms import functional as TF
from scoped_engine import build_model
from scoped_metrics import decode
from determinism_policy import math_attention
from parity_contract import compare

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False)
def tensor(image):
    with Image.open(image['path']) as im:return TF.normalize(TF.resize(TF.to_tensor(im.convert('RGB')),[512,512],antialias=False),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0)
class Packed(torch.nn.Module):
    def __init__(self,net):super().__init__();self.net=net
    def forward(self,x):
        boxes,logits=self.net(x)
        return torch.cat([boxes,logits[:,:,:615]],dim=2)

@math_attention()
def main():
    plan=read(HERE/'EXPORT_PLAN.json')
    approval_path=HERE/'approval.json'
    if not approval_path.exists():raise ValueError('Separate local export scope approval is required; no export started')
    approval=read(approval_path)
    if approval.get('approved') is not True or approval.get('export_plan_sha256')!=sha(HERE/'EXPORT_PLAN.json') or not approval.get('user_authorization_evidence'):raise ValueError('Exact separate export approval missing')
    for p,h in plan['input_hashes'].items():assert sha(p)==h
    for p,h in plan['code_hashes'].items():assert sha(p)==h
    assert all(importlib.metadata.version(p)==v for p,v in plan['runtime_versions'].items())
    result=read(EVAL/'comparison.json');lock=read(EVAL/'evaluation-lock.json')
    assert result['evidence_gate_passed'] and result['selected_step']==100
    assert sha(EVAL/'evaluation-lock.json')==result['evaluation_lock_sha256']
    ck=lock['checkpoints']['candidate'];assert ck['sha256']=='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3'
    out=HERE/'export-output-v1';out.mkdir(exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    weights=Path(plan['pretrained_weights']);net=build_model(weights,TOOLS/'rf-mapping.json').cpu().eval()
    loaded=torch.load(ck['path'],map_location='cpu',weights_only=True)
    assert loaded['step']==100 and loaded['frametrail']['actual_job_id']=='7805570'
    net.load_state_dict(loaded['model_state_dict'],strict=True);del loaded
    probes={digest:lock['images'][digest] for digest in plan['raw_parity_probe_sha256']}
    before={}
    for digest,image in probes.items():
        with torch.inference_mode():raw=net(tensor(image))
        before[digest]={k:v.detach().cpu().numpy() for k,v in raw.items() if k in ('pred_boxes','pred_logits')}
    clone=copy.deepcopy(net).eval();clone.export();packed=Packed(clone).eval()
    onnx_path=out/'rfdetr_balanced7805570_step100.onnx'
    torch.onnx.export(packed,tensor(next(iter(probes.values()))),str(onnx_path),input_names=['input'],output_names=['output'],opset_version=17,dynamo=False)
    exported=onnx.load(onnx_path)
    names=read(TOOLS/'rf-mapping.json')['canonical_class_names'];names=[names[str(i)] for i in range(615)] if isinstance(names,dict) else names
    for key,value in {'frametrail.profile':'rfdetr-7805570','frametrail.vocabulary':'\n'.join(names),'frametrail.checkpoint_sha256':ck['sha256'],'frametrail.preprocessing':'rf-rgb512-normalized-v1','frametrail.experimental':'true','frametrail.training_job':'7805570','frametrail.training_step':'100'}.items():
        prop=exported.metadata_props.add();prop.key=key;prop.value=value
    onnx.checker.check_model(exported);onnx.save(exported,onnx_path)
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(onnx_path),sess_options=options,providers=['CPUExecutionProvider'])
    assert session.get_inputs()[0].shape==[1,3,512,512] and session.get_outputs()[0].shape==[1,300,619]
    records=[];timings=[]
    for index,(digest,image) in enumerate(lock['images'].items(),1):
        x=tensor(image);started=time.perf_counter();raw=session.run(None,{'input':x.numpy()})[0];seconds=time.perf_counter()-started
        assert raw.shape==(1,300,619) and np.isfinite(raw).all()
        logits=torch.cat([torch.from_numpy(raw[:,:,4:]),torch.zeros(1,300,1)],dim=2)
        detections=decode(dict(pred_boxes=torch.from_numpy(raw[:,:,:4]),pred_logits=logits),image['width'],image['height'])
        expected=read(EVAL/'candidate/images'/f'{digest}.json')['detections']
        compared=compare(expected,detections,image['width'],image['height'])
        raw_parity=None
        if digest in probes:
            boxes=before[digest]['pred_boxes'];scores=before[digest]['pred_logits'][:,:,:615]
            raw_parity=dict(boxes_allclose=bool(np.allclose(boxes,raw[:,:,:4],rtol=1e-4,atol=.002)),logits_allclose=bool(np.allclose(scores,raw[:,:,4:],rtol=1e-4,atol=.002)),max_box_error=float(np.max(np.abs(boxes-raw[:,:,:4]))),max_logit_error=float(np.max(np.abs(scores-raw[:,:,4:]))))
        record=dict(image_sha256=digest,comparison=compared,raw_parity=raw_parity,ORT_seconds=seconds,detections=detections)
        save(out/'parity'/f'{digest}.json',record);records.append(record)
        if index%20==0:print(f'ORT parity {index}/{len(lock["images"])}',flush=True)
    for digest,image in probes.items():
        x=tensor(image).numpy()
        for _ in range(2):session.run(None,{'input':x})
        values=[]
        for _ in range(5):
            started=time.perf_counter();session.run(None,{'input':x});values.append(time.perf_counter()-started)
        timings.append(dict(image_sha256=digest,seconds=values,median_seconds=float(np.median(values))))
    passed=all(r['comparison']['passed'] and (r['raw_parity'] is None or (r['raw_parity']['boxes_allclose'] and r['raw_parity']['logits_allclose'])) for r in records)
    for p,h in plan['input_hashes'].items():assert sha(p)==h
    receipt=dict(status='local-export-parity-passed' if passed else 'export-held-parity-failed',checkpoint_sha256=ck['sha256'],ONNX_sha256=sha(onnx_path),decoded_parity_images=len(records),raw_parity_probes=len(probes),parity_passed=passed,timing=timings,timing_limits='ORT CPU forward latency only, not native app end-to-end FPS; no native performance gate claimed.',input_shape=[1,3,512,512],output_shape=[1,300,619],profile='rfdetr-7805570',new_GPU_jobs=0,training_updates=0,application_files_changed=False,approved_for_application=False)
    save(out/'EXPORT_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))
    if not passed:raise SystemExit('Export parity failed; keep artifact for inspection; no adoption')

if __name__=='__main__':main()
