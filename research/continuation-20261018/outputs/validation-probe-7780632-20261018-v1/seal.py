"""Seal the completed validation diagnostic into a fresh user-facing directory."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
D=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\validation-probe-7780632-20261018-v1')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
inputs=read(P/'INPUT_INTEGRITY.json')['files']
assert all(sha(Path(i['path']))==i['sha256'] for i in inputs)
v=read(P/'VALIDATION_RECEIPT.json');g=read(P/'GALLERY_VALIDATION.json');s=read(P/'SUMMARY.json')
assert v['status']==g['status']=='pass' and v['full_model_forwards']==30 and v['raw_target_stage_checks']==168
assert v['all_24_new_class_targets_have_distinct_covering_decoder_queries']
assert all(c['steps'][1]['stages']['decoder']['targets_with_any_box_iou_at_least_half']==c['known_misses'] for c in s['classes'])
receipt=dict(status='complete-sealed-validation-diagnostic',job='7780632',input_files_rehashed=len(inputs),input_changes=0,
    photos=15,full_model_forwards=30,known_misses=28,new_class_misses=24,
    new_class_targets_with_distinct_covering_decoder_queries=24,new_class_targets_below_required_confidence_on_covering_queries=24,
    cpu_kit_decoded_parity_passed=True,raw_stage_checks=168,gallery_checks_passed=True,
    optimizer_updates=0,heldout_used=False,model_export=False,application_adoption=False,
    numerical_training_gradient_check='prepared-not-executed',
    next_best_step='Training-only classification-loss and row-gradient diagnostic without optimizer updates, before proposing more GPU optimization.')
(P/'FINAL_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(P/'USE.txt').write_text('Read REPORT.md for the conclusion and index.html for the 28 visual target diagnostics.\nThis is a sealed evidence bundle, not an app installer or trained model. No weights are included.\nTo reproduce, copy the scripts into a fresh work directory and use the pinned local CPU runtime and original inputs. Do not rerun scripts inside this sealed directory.\nThe follow-up training-only gradient diagnostic is prepared, not executed; it makes no optimizer updates.\n',encoding='utf-8')
assert not D.exists(),'Refusing to overwrite an existing published version'
D.mkdir(parents=True)
for source in P.iterdir():
    if source.is_file():shutil.copy2(source,D/source.name)
    elif source.name in ('photos','raw'):shutil.copytree(source,D/source.name)
manifest=[dict(file=p.relative_to(D).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(D.rglob('*')) if p.is_file()]
(D/'files-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
assert all(sha(D/m['file'])==m['sha256'] for m in manifest)
print(json.dumps(dict(status='sealed-and-copy-verified',output=str(D),files=len(manifest),bytes=sum(m['bytes'] for m in manifest),original_inputs_unchanged=len(inputs)),indent=2))
