from pathlib import Path
import hashlib,json,runpy

APP=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail')
STAGE=Path(__file__).parent
helpers=runpy.run_path(str(STAGE/'sync_frametrail_progress.py'))
manifest=json.loads((APP/'research/SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
inventory=json.loads((APP/'research/LOCAL_ARTIFACT_INVENTORY.json').read_text(encoding='utf-8'))
seen={r['path'] for r in manifest['files']};added=0
sources=[('local-packages',APP/'out',list((APP/'out').rglob('*'))),('model-metadata',APP/'models',list((APP/'models').rglob('*'))),('local-media-results',APP,[p for p in APP.iterdir() if p.suffix.lower() in {'.mp4','.frametrail'} or p.name.endswith('-analysis.csv')])]
for name,root,files in sources:
 inventory['source_roots'][name]=str(root)
 for p in files:
  if not p.is_file():continue
  rel=p.relative_to(root);key=name+'/'+rel.as_posix();parts={x.lower() for x in rel.parts}
  selected=p.suffix.lower() in {'.md','.json','.sha256','.csv'} or p.name.lower() in {'readme.txt','read-me.txt'}
  if parts & {'notices','licenses','third-party-licenses'}:selected=False
  if not selected:
   inventory['files'].append({'source_root':name,'path':rel.as_posix(),'bytes':p.stat().st_size,'reason':'local-media-model-package-or-third-party-runtime'});continue
  if key in seen:raise RuntimeError(f'Duplicate addition {key}')
  raw=p.read_bytes();decoded=raw.decode('utf-8-sig')
  for label,pattern in helpers['SECRETS']:
   if pattern.search(decoded):raise RuntimeError(f'Credential-pattern alert {key}: {label}')
  dest=APP/'research'/key;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  digest=hashlib.sha256(raw).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
  manifest['files'].append({'path':key,'bytes':len(raw),'sha256':digest});seen.add(key);added+=1
for rel,obj in [('SOURCE_MANIFEST.json',manifest),('LOCAL_ARTIFACT_INVENTORY.json',inventory)]:
 (APP/'research'/rel).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
p=APP/'research/sync-20261024/VALIDATION_RECEIPT.json';receipt=json.loads(p.read_text(encoding='utf-8'))
receipt.update(archived_source_files=len(manifest['files']),archived_source_bytes=sum(r['bytes'] for r in manifest['files']),excluded_local_files=len(inventory['files']))
receipt['validation']['initial_copied_archive_independent_sha256_check']={'status':'passed','files':27814}
receipt['validation']['additional_package_model_and_demo_metadata']={'scanned_and_copy_hash_verified':added,'status':'passed'}
p.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
p=APP/'research/README.md';text=p.read_text(encoding='utf-8').replace('- [Source manifest]', '- `local-packages/`, `model-metadata/` and `local-media-results/`: package manifests/checksums, export receipts and the local demonstration analysis CSV; binary assets remain local.\n- [Source manifest]');p.write_text(text,encoding='utf-8')
print(json.dumps({'additional_metadata_files':added,'total_source_files':len(manifest['files']),'total_source_bytes':sum(r['bytes'] for r in manifest['files']),'total_excluded_local_files':len(inventory['files'])}))
