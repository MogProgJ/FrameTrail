"""Prepare bounded CPU data collection under the standing user authorization."""
import hashlib,json,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'billboard-data-refresh-7818553-20261018-v1';T=P/'data-tools-v1'
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def main():
    T.mkdir(parents=True,exist_ok=False);oldtools=OLD/'nextdata-acquisition-7768932-v1/next-photo-tools-v1'
    raw=read(OLD/'nextdata-acquisition-7768932-v1/results-7769109/retrieved/output/training-general-v1/next-photo-7768932-v1/manifest.json')
    gap=read(OLD/'gap363-acquisition-7786444-v1/results-7787611/retrieved/output/training-general-v1/gap-photo-meta-7786444-v1/manifest.json');prior=read(oldtools/'prior-intake-index.json');current=read(D.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release/candidate-manifest-v2.json')
    exclusion={}
    for r in prior['images']+raw['images']+gap['images']:
        exclusion[r['id']]=dict(id=r['id'],sha256=r['sha256'],dhash=r['dhash'],group_id=r.get('group_id',''),author_alias=r.get('author_alias',''),author_url=r.get('attribution',{}).get('author_url',''))
    for r in current['images']:
        assert r['image_id'] in exclusion,'Current release escaped full intake history'
    save(T/'exclusions.json',dict(images=list(exclusion.values()),known_current_identity_groups=sorted({r['identity_group'] for r in current['images']})))
    save(T/'classes-source.json',dict(classes=raw['classes'],source=raw['source']))
    plan=dict(schema=1,purpose='new-billboard-and-confuser-photo-source-intake-only',authorization='User approved continued bounded FrameTrail work without routine approval prompts on18October2026; exact scope recorded before submission. No training/adoption authorization inferred from new labels.',catalogue_relative_path='output/training-general-v1/catalogue-7447265/openimages-train.sqlite',catalogue_sha256='bd42dbb1129406c16cda37401670ecba04d6d956cde0071ab79de6190162e78d',exclusions_sha256=sha(T/'exclusions.json'),classes_source_sha256=sha(T/'classes-source.json'),selection_seed='frametrail-data-refresh-after7818553-v1',anchors=[dict(name='billboard',raw_id=46,quota=dict(train=72,val=24,test=24))]+[dict(name=name,raw_id=rawid,quota=dict(train=14,val=5,test=5)) for rawid,name in [(549,'traffic sign'),(575,'washing machine'),(386,'picture frame'),(128,'computer monitor'),(585,'whiteboard')]],maximum_photos=240,maximum_photos_per_author_alias=1,split='Before downloading/predictions: stable SHA256 author group buckets0-1test,2-3val,4-9train. Quotas fixed; shortages preserved without substitute categories/authors or retries. Resolved NSID and perceptual/source identity checks remain mandatory before release.',publisher_policy='Existing pinned publisher TRAIN catalogue only; original image bytes from public OpenImages AWS train endpoint, CC-BY2.0 publisher metadata and identity rotation. Individual public Flickr source HTML evidence collected separately, with no rights/training clearance.',model_inference=False,training=False,maximum_original_bytes=1000000000,maximum_HTML_bytes=480000000,maximum_source_page_bytes=2000000,maximum_image_bytes=10000000,decoded_pixel_cap=40000000,wall_minutes=45,active_seconds_cap=2400,CPU_cores=2,host_memory_GiB=8,partition='cpu_il',GPUs=0,automatic_retries=0,automatic_replacement_jobs=0,shortfalls='Keep partial cohort and holds; no silent replacements or fallback sources.',sources=['https://storage.googleapis.com/openimages/web/factsfigures_v7.html','https://storage.googleapis.com/openimages/web/download_v7.html'],rights_verified=False,approved_for_training=False,approved_for_application=False)
    save(T/'collection-plan.json',plan);save(P/'SCOPE.json',plan)
    for name in ('photo_transport.py','source_transport.py'):shutil.copy2(oldtools/name,T/name)
    for name in ('collector.py','test_collector.py'):shutil.copy2(D/name,T/name)
    save(P/'USER_AUTHORIZATION.json',dict(verbatim_user_authorization="Yeah, it's approved, man. You don't have to ask for my approval on this. All right, always just keep working and working and working.",standing_instruction='Latest user AGENTS.md explicitly authorizes bounded cluster continuation without routine approval prompts. This package is a CPU-only data intake within45minutes/two CPUs/8GiB, no GPUs, retries, training or automatic rights clearance.',scope_plan_sha256=sha(T/'collection-plan.json')))
    print(json.dumps(dict(proposal=str(P),excluded_previously_acquired_photos=len(exclusion),maximum_new_photos=240,GPUs=0)))
if __name__=='__main__':main()
