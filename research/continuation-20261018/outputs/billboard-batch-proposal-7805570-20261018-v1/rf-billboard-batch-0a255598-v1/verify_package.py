"""Read-only code and asset validation; no inference or submission."""
import argparse,json
from pathlib import Path
from continuation_guard import sha,read,inputs
T=Path(__file__).resolve().parent
def verify(preparation_only=False):
    seal=read(T/'package-files.json')
    for name,digest in seal['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or sha(T/p)!=digest:raise ValueError('Changed or escaping package file: '+name)
    for index in range(4):release,schedule,_,_=inputs(T,require_approval=not preparation_only,task_index=index)
    return dict(status='proposed-code-assets-and-scope-verified-no-cluster-approval' if preparation_only else 'approved-code-assets-and-scope-verified',sealed_files=len(seal['files']),photos=len(release['images']),planned_updates=len(schedule)*4,trial_tasks=4,GPU_inference=False,training=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--preparation-only',action='store_true');a=p.parse_args();print(json.dumps(verify(a.preparation_only)))
