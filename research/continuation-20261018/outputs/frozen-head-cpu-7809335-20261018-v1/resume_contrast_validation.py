"""Resume validation after a logging import error; do not refit candidates."""
import json,time
from run_reviewed_contrast import HERE,TOOLS,read,save,sha,torch
from run_local_probes import predict
from selection_policy import eligible,ranking,evaluate
OUT=HERE/'reviewed-contrast'
torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
plan=read(OUT/'PLAN.json');release=read(TOOLS/'release/candidate-manifest-v2.json');val=[r for r in release['images'] if r['split']=='val']
baseline=read(HERE/'local-probes/validation-baseline.json');original=read(TOOLS/'inputs/validation-original.json');best=baseline;selected=None;records=[]
for recipe in plan['recipes']:
    i=recipe['index'];head=torch.load(OUT/f'head-{i}.pt',map_location='cpu',weights_only=True);fit=read(OUT/f'fit-{i}.json');assert fit['index']==i and fit['ridge']==recipe['ridge']
    path=OUT/f'validation-{i}.json'
    if path.exists():
        result=read(path);rescored=evaluate(val,result['predictions']);assert result['metrics']==rescored['metrics'] and result['per_class']==rescored['per_class'];seconds=None
    else:result,seconds=predict(val,head);save(path,result)
    ok=eligible(result,baseline) and eligible(result,original);strict=ok and ranking(result)>ranking(best) and ranking(result)>ranking(original)
    if strict:best=result;selected=i
    bill=result['per_class']['133'];record=dict(recipe,eligible=ok,strict_gain=bool(strict),billboard_known_hits=bill['complete_tp']+bill['partial_hits'],billboard_complete_fp=bill['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],ranking=list(ranking(result)),validation_seconds=seconds);records.append(record);print(json.dumps(record),flush=True)
save(OUT/'RECEIPT.json',dict(status='reviewed-training-region-local-probes-complete',plan_sha256=sha(OUT/'PLAN.json'),selected_index=selected,trials=records,original_data_labels_and_scopes_unchanged=True,new_region_overlay_assistant_reviewed=True,validation_or_test_used_in_training=False,all_other_model_weights_unchanged=True,new_GPU_jobs=0,production_adoption=False,strict_ONNX_hold_not_waived=True,resumed_after='Logging NameError after candidate0 validation was saved; all four fitted heads reused without optimizer updates or reselection of recipes.'))
