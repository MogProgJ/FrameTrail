"""Inventory and copy FrameTrail progress; never execute archived experiments."""
from pathlib import Path
from collections import Counter
import argparse, gzip, hashlib, json, re, shutil, os, subprocess

APP = Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail')
CONT = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
STAGE = Path(__file__).parent
TEXT = {'.md','.json','.jsonl','.py','.ps1','.sh','.sbatch','.cmd','.bat','.txt','.log','.csv','.tsv','.yaml','.yml','.toml','.ini','.cfg','.cpp','.c','.hpp','.h','.ui','.qrc','.cmake','.js','.cjs','.mjs','.html','.css','.svg','.sha256','.patch','.diff','.in'}
BLOCK_PARTS = {'.git','.deps','.venv','__pycache__','node_modules','build','cmakefiles','exporter-overlay','runtime-temp','cluster-access-20261022-v1'}
SECRETS = [
 ('private-key',re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----')),
 ('github-token',re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
 ('openai-key',re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b')),
 ('aws-key',re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
 ('slack-token',re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b')),
 ('credential-url',re.compile(r'https?://[^\s/@:]+:[^\s/@]+@')),
 ('assigned-secret',re.compile(r'''(?im)^\s*["']?(?:password|passwd|api_key|access_token|auth_token|client_secret)["']?\s*[:=]\s*["']([^"'\n]{12,})["']''')),
]

def sha(data): return hashlib.sha256(data).hexdigest()
def reason(p, rel):
 parts={x.lower() for x in rel.parts}
 if parts & BLOCK_PARTS:return 'dependency-build-runtime-or-authentication'
 if p.name.lower().startswith('.env') or p.suffix.lower() in {'.pem','.key','.pfx','.p12'} or p.name.lower().startswith(('id_rsa','id_ed25519')):return 'local-authentication'
 if p.name=='debug.log':return 'browser-runtime-log'
 if p.suffix.lower() not in TEXT and not p.name.endswith(('.json.gz','.jsonl.gz','.csv.gz')) and p.name not in {'.gitignore','.gitattributes'}:return 'media-model-binary-or-generated-archive'
 if p.stat().st_size>50*1024*1024:return 'large-generated-data'
 return None

def dump(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def copy_plan():
 plan=json.loads((STAGE/'github-sync-plan.json').read_text(encoding='utf-8'))
 if plan['secret_scan_alerts']:raise RuntimeError('Unresolved secret scan alerts')
 included=json.loads((STAGE/'github-sync-included.json').read_text(encoding='utf-8'))
 excluded=json.loads((STAGE/'github-sync-excluded.json').read_text(encoding='utf-8'))
 for i,row in enumerate(included):
  rootname,rel=row['path'].split('/',1);root=CONT if rootname=='continuation-20261018' else APP/'output'
  raw=(root/rel).read_bytes()
  if sha(raw)!=row['sha256']:raise RuntimeError(f'Source changed after scan: {row["path"]}')
  dest=APP/'research'/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists() and dest.read_bytes()!=raw:raise RuntimeError(f'Archive collision: {row["path"]}')
  if not dest.exists():dest.write_bytes(raw)
  if i%2500==0:print(f'Copied and verified {i}/{len(included)}',flush=True)
 dump(APP/'research/SOURCE_MANIFEST.json',{'schema':1,'as_of':'2026-10-24','policy':'Original bytes retained; paths relative to research/. Archived scripts and experiments were not rerun.','files':included})
 dump(APP/'research/LOCAL_ARTIFACT_INVENTORY.json',{'schema':1,'as_of':'2026-10-24','note':'Excluded local files remain preserved at the source roots. Size/path inventory is not a binary backup. Existing scientific receipts contain artifact hashes.','source_roots':{'continuation-20261018':str(CONT),'local-output':str(APP/'output')},'files':excluded})
 print(json.dumps({'copied_and_hash_verified':len(included),'excluded_local_files':len(excluded)}))

def inventory(copy=False):
 included=[];excluded=[];alerts=[];tot=Counter();groups=Counter()
 for root,dest in [(CONT,'continuation-20261018'),(APP/'output','local-output')]:
  for folder,dirs,files in os.walk(root):
   for name in files:
    p=Path(folder)/name;rel=p.relative_to(root);out=APP/'research'/dest/rel;why=reason(p,rel)
    if why:
     excluded.append({'source_root':dest,'path':rel.as_posix(),'bytes':p.stat().st_size,'reason':why});tot[why]+=1;continue
    raw=p.read_bytes()
    try:
     decoded=(gzip.decompress(raw) if p.name.endswith('.gz') else raw).decode('utf-8-sig')
    except (UnicodeError,OSError,EOFError):
     excluded.append({'source_root':dest,'path':rel.as_posix(),'bytes':len(raw),'reason':'non-text-payload'});continue
    if re.search(r'data:image/[^;]+;base64,',decoded,re.I):
     excluded.append({'source_root':dest,'path':rel.as_posix(),'bytes':len(raw),'reason':'embedded-image-payload'});continue
    for label,pattern in SECRETS:
     if pattern.search(decoded):alerts.append({'path':f'{dest}/{rel.as_posix()}','pattern':label})
    record={'path':f'{dest}/{rel.as_posix()}','bytes':len(raw),'sha256':sha(raw)}
    included.append(record);groups[f'{dest}/{rel.parts[0]}']+=1
    if copy:
     out.parent.mkdir(parents=True,exist_ok=True)
     if out.exists() and out.read_bytes()!=raw:raise RuntimeError(f'Refuse overwrite changed archive {out}')
     if not out.exists():shutil.copyfile(p,out)
 result={'schema':1,'as_of':'2026-10-24','included_files':len(included),'included_bytes':sum(x['bytes'] for x in included),'excluded_files':len(excluded),'secret_scan_alerts':alerts,'excluded_reason_counts':dict(Counter(x['reason'] for x in excluded)),'groups':dict(groups)}
 dump(STAGE/'github-sync-plan.json',result)
 dump(STAGE/'github-sync-included.json',included);dump(STAGE/'github-sync-excluded.json',excluded)
 print(json.dumps(result,indent=2))
 if copy:
  dump(APP/'research'/'SOURCE_MANIFEST.json',{'schema':1,'as_of':'2026-10-24','policy':'Original bytes retained; paths are relative to research/. No archived script or experiment was rerun.','files':included})
  dump(APP/'research'/'LOCAL_ARTIFACT_INVENTORY.json',{'schema':1,'as_of':'2026-10-24','note':'Excluded local files remain preserved at the source roots. Models/media/builds are not Git artifacts; existing source receipts contain scientific artifact hashes. Size/path inventory is not a backup of excluded contents. Authentication/runtime files are intentionally omitted.','source_roots':{'continuation-20261018':str(CONT),'local-output':str(APP/'output')},'files':excluded})
 if alerts:raise SystemExit('Review scan alerts before staging/pushing')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--copy',action='store_true');parser.add_argument('--copy-plan',action='store_true');parser.add_argument('--main-scan',action='store_true');args=parser.parse_args()
 if args.copy_plan:copy_plan();raise SystemExit(0)
 if args.main_scan:
  paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=APP).decode().split('\0'); alerts=[];count=0
  for rel in sorted(set(paths)):
   if not rel or rel.startswith('research/'):continue
   p=APP/rel
   if not p.is_file() or reason(p,Path(rel)):continue
   count+=1;decoded=p.read_text(encoding='utf-8-sig')
   for label,pattern in SECRETS:
    if pattern.search(decoded):alerts.append({'path':rel,'pattern':label})
  print(json.dumps({'files_scanned':count,'alerts':alerts}));raise SystemExit(bool(alerts))
 inventory(args.copy)
