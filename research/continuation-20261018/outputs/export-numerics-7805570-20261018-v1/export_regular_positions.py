"""Test tracing the unchanged regular forward rather than export rewrites."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent/'export-parity-preparation-7805570-20261018-v1'
sys.path.insert(0,str(EXP));import export_and_check as e
import torch,numpy as np,onnxruntime as ort
class Regular(torch.nn.Module):
 def __init__(self,net):super().__init__();self.net=net
 def forward(self,x):
  out=self.net(x);return torch.cat([out['pred_boxes'],out['pred_logits'][:,:,:615]],dim=2)
@e.math_attention()
def main():
 torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 plan=e.read(EXP/'EXPORT_PLAN.json');lock=e.read(e.EVAL/'evaluation-lock.json')
 net=e.build_model(Path(plan['pretrained_weights']),e.TOOLS/'rf-mapping.json').cpu().eval()
 net.load_state_dict(torch.load(lock['checkpoints']['candidate']['path'],map_location='cpu',weights_only=True)['model_state_dict'])
 for p in net.parameters():p.requires_grad_(False)
 for module in net.modules():
  if module.__class__.__name__=='DinoV2':module.export()
 x=e.tensor(next(iter(lock['images'].values())))
 path=HERE/'regular-positions.onnx'
 assert not path.exists()
 torch.onnx.export(Regular(net),x,str(path),input_names=['input'],output_names=['output'],opset_version=17,dynamo=False)
 records=[]
 options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
 session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
 for r in e.read(HERE/'DIAGNOSIS.json'):
  digest=r['image_sha256'];image=lock['images'][digest];x=e.tensor(image);raw=session.run(None,{'input':x.numpy()})[0]
  with torch.inference_mode():a=net(x)
  b=dict(pred_boxes=torch.from_numpy(raw[:,:,:4]),pred_logits=torch.cat([torch.from_numpy(raw[:,:,4:]),torch.zeros(1,300,1)],dim=2))
  expected=e.read(e.EVAL/'candidate/images'/f'{digest}.json')['detections']
  comparison=e.compare(expected,e.decode(b,image['width'],image['height']),image['width'],image['height'])
  records.append(dict(image_sha256=digest,comparison=comparison));print(json.dumps(records[-1]),flush=True)
 (HERE/'REGULAR_POSITIONS_DIAGNOSIS.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
if __name__=='__main__':main()
