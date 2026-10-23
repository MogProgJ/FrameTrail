import sys,json,copy
from pathlib import Path
BASE=Path(__file__).resolve().parent;EXP=BASE.parent/'export-parity-preparation-7805570-20261018-v1';EVAL=BASE.parent/'heldout-evaluation-7805570-20261018-v1'
sys.path.insert(0,str(EXP));import export_and_check as e
import torch,numpy as np,onnxruntime as ort
from scipy.optimize import linear_sum_assignment
read=e.read
@e.math_attention()
def main():
 torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 plan=read(EXP/'EXPORT_PLAN.json');lock=read(EVAL/'evaluation-lock.json');net=e.build_model(Path(plan['pretrained_weights']),e.TOOLS/'rf-mapping.json').eval()
 net.load_state_dict(torch.load(lock['checkpoints']['candidate']['path'],map_location='cpu',weights_only=True)['model_state_dict']);clone=copy.deepcopy(net);clone.export()
 sessions={}
 for label,level in [('disabled',ort.GraphOptimizationLevel.ORT_DISABLE_ALL),('basic',ort.GraphOptimizationLevel.ORT_ENABLE_BASIC),('all',ort.GraphOptimizationLevel.ORT_ENABLE_ALL)]:
  options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1;options.graph_optimization_level=level
  sessions[label]=ort.InferenceSession(str(EXP/'export-output-v1/rfdetr_balanced7805570_step100.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
 failed=[f.stem for f in (EXP/'export-output-v1/parity').glob('*.json') if not read(f)['comparison']['passed']]
 probes=list(dict.fromkeys(failed+plan['raw_parity_probe_sha256']));results=[]
 for digest in probes:
  image=lock['images'][digest];x=e.tensor(image)
  with torch.inference_mode():a=net(x);boxes,logits=clone(x)
  b=dict(pred_boxes=boxes,pred_logits=logits);expected=e.decode(a,image['width'],image['height'])
  row=dict(image_sha256=digest,export_clone=e.compare(expected,e.decode(b,image['width'],image['height']),image['width'],image['height']),runtimes={})
  original=np.concatenate([a['pred_boxes'].numpy(),a['pred_logits'][:,:,:615].numpy()],axis=2)[0]
  clone_raw=np.concatenate([boxes.numpy(),logits[:,:,:615].numpy()],axis=2)[0]
  for label,session in sessions.items():
   raw=session.run(None,{'input':x.numpy()})[0]
   outputs=dict(pred_boxes=torch.from_numpy(raw[:,:,:4]),pred_logits=torch.cat([torch.from_numpy(raw[:,:,4:]),torch.zeros(1,300,1)],dim=2))
   cost=np.sum((original[:,None,:4]-raw[0,None,:,:4])**2,axis=2)
   ai,bi=linear_sum_assignment(cost);aligned=raw[0,bi];close=np.abs(original-aligned)
   row['runtimes'][label]=dict(decoded=e.compare(expected,e.decode(outputs,image['width'],image['height']),image['width'],image['height']),permutation_count=int(np.sum(ai!=bi)),aligned_max_box_error=float(close[:,:4].max()),aligned_max_logit_error=float(close[:,4:].max()),ORT_vs_clone_max=float(np.abs(clone_raw-raw[0]).max()))
  results.append(row);print(json.dumps(row),flush=True)
 (BASE/'DIAGNOSIS.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
if __name__=='__main__':main()
