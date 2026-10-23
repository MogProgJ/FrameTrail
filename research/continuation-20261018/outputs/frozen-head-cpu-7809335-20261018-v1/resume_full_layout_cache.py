"""Preserve partial trimmed-cache evidence; build a new exact-layout cache."""
import hashlib,time
from cache_engine import *
from build_cache import WEIGHTS,save
from scoped_engine import build_model,load_sample
from continuation_guard import read,sha
from determinism_policy import math_attention
from verify_cache_parity import fingerprint
@math_attention()
def run():
    parity=read(HERE/'CACHE_PARITY_FULL_LAYOUT.json');assert parity['cache_engine_sha256']==sha(HERE/'cache_engine.py')
    assert all(r['passed'] for r in parity['records'])
    plan=read(HERE/'LOCAL_EXPERIMENT_PLAN.json');assert plan['ridge_strengths']==[.1,1.,10.,100.]
    cache_dir=HERE/'cache-full-layout';cache_dir.mkdir(exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();ck=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)
    net.load_state_dict(ck['model_state_dict']);del ck
    for p in net.parameters():p.requires_grad_(False)
    before=fingerprint(net);w=net.class_embed.weight.detach().clone();b=net.class_embed.bias.detach().clone()
    torch.save(dict(weight=w,bias=b),cache_dir/'initial-head.pt')
    release=read(TOOLS/'release/candidate-manifest-v2.json');pools=read(TOOLS/'sampling-pools.json');ids=set(pools['billboard']+pools['explicit_negative'])
    rows=[r for r in release['images'] if r['image_id'] in ids or r['split']=='val'];assert len(rows)==190
    metadata={};started=time.perf_counter()
    for i,row in enumerate(rows,1):
        assert sha(TOOLS/'release'/row['source_path'])==row['image_sha256']
        image,_=load_sample(TOOLS/'release',row)
        with torch.no_grad():
            cache,live=capture(net,image,full=row['split']=='train');rebuilt=replay(cache,w,b);error=max_output_error(live,rebuilt)
        assert error==0,(row['image_id'],error)
        path=cache_dir/(row['image_id']+'.pt');torch.save(cache,path)
        metadata[row['image_id']]=dict(split=row['split'],source_sha256=row['image_sha256'],cache_sha256=sha(path),forward_max_error=error)
        if i%20==0:print(f'Exact-layout CPU cache {i}/190; every output bitwise identical',flush=True)
    assert fingerprint(net)==before
    save(HERE/'CACHE_INDEX_FULL_LAYOUT.json',metadata)
    save(HERE/'CACHE_RECEIPT_FULL_LAYOUT.json',dict(status='190-exact-layout-cache-forward-parity-passed',training_images=55,development_images=135,full_model_state_unchanged=True,all190_forward_errors_zero=True,optimizer_updates=0,new_GPU_jobs=0,seconds=time.perf_counter()-started,bytes=sum(p.stat().st_size for p in cache_dir.glob('*.pt')),plan_sha256=sha(HERE/'LOCAL_EXPERIMENT_PLAN.json'),original_trimmed_cache_preserved=True))
if __name__=='__main__':run()
