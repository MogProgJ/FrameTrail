"""Verify and exclusively extract an actual bounded Slurm result; never adopts a model."""
import argparse,hashlib,json,tarfile
from pathlib import Path,PurePosixPath

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--job',required=True);a=ap.parse_args();assert a.job.isdigit();archive=a.archive.resolve(strict=True);side=archive.with_suffix(archive.suffix+'.sha256');expected=side.read_text().split()[0];assert len(expected)==64 and sha(archive)==expected
 out=archive.parent/('verified-'+a.job);assert not out.exists(),'Existing verified extraction preserved';members=[]
 with tarfile.open(archive,'r:gz') as tar:
  total=0
  for m in tar.getmembers():
   p=PurePosixPath(m.name)
   if p.is_absolute() or '..' in p.parts or not(m.isdir() or m.isfile()) or '\\' in m.name or ':' in m.name:raise ValueError('Unsafe archive entry')
   allowed=m.name.startswith('output/rf-nextdata-'+a.job+'/') or m.name=='output/rf-nextdata-'+a.job or m.name=='frametrail-rf-nextdata-'+a.job+'.log'
   if not allowed or m.size>1024**3:raise ValueError('Unexpected/oversize result entry')
   total+=m.size;members.append(m)
  if total>4*1024**3 or len(members)>1000 or len({m.name for m in members})!=len(members):raise ValueError('Result bounds/duplicates invalid')
  transfer=tar.extractfile('output/rf-nextdata-'+a.job+'/transfer.json');receipt=json.load(transfer);assert receipt['actual_job_id']==a.job
  out.mkdir()
  for m in members:
   dest=out/Path(*PurePosixPath(m.name).parts);assert dest.resolve().is_relative_to(out)
   if m.isdir():dest.mkdir(parents=True,exist_ok=True)
   else:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(tar.extractfile(m).read())
 base=out/'output'/('rf-nextdata-'+a.job);report=base/'experiment-report.json';status='partial-job-output-preserved'
 if report.exists():
  r=json.loads(report.read_text());pre=json.loads((base/'preflight.json').read_text());protocol=json.loads((Path(__file__).parent/'rf-nextdata-tools-v1/protocol.json').read_text());assert r['actual_job_id']==a.job and r['updates']==600 and receipt['process_exit_code']==0 and receipt['finalized'];assert pre['protocol_sha256']==sha(Path(__file__).parent/'rf-nextdata-tools-v1/protocol.json') and pre['candidate_sha256']==protocol['candidate_sha256'];assert sha(base/'best.pt')==r['best_checkpoint_sha256'] and sha(base/'last.pt')==r['last_checkpoint_sha256'];assert r['frozen_features_and_boxes_unchanged'] and r['inactive_classifier_rows_unchanged'];assert pre['test_photos_used']==0 and pre['fresh_video_frames_used']==0;status='trial-verified-awaiting-frozen-heldout-evaluation'
 result=dict(status=status,actual_job_id=a.job,archive_sha256=expected,process_exit_code=receipt['process_exit_code'],output=str(base),approved_for_application=False)
 with (archive.parent/'verification-receipt.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
