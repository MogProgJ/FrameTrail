"""Compare fixed validation-selected states; never choose using known regression."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
identity=json.loads((HERE/'PROPOSAL_IDENTITY.json').read_text());sys.path.insert(0,str(HERE/identity['package_directory']))
from continuation_guard import read,sha
from selection_policy import ranking
def compare(retrieval):
    rows=[];complete=True
    for i in range(4):
        matches=list((retrieval/('task-'+str(i))).glob('verified-*/output/rf-selector-*'))
        if len(matches)!=1:raise ValueError('Need all four verified task outputs, including failures')
        out=matches[0];t=read(out/'transfer.json')
        if t['training_exit_code']!=0:
            rows.append(dict(index=i,status='training-failed-or-partial',exit_code=t['training_exit_code']));complete=False;continue
        r=read(out/'experiment-report.json');v=read(out/f"validation-{r['best_step']:04}.json")
        if sha(out/'best.pt')!=r['best_checkpoint_sha256']:raise ValueError('Selected checkpoint changed')
        reg=read(out/'known-regression.json') if (out/'known-regression.json').exists() else None
        rows.append(dict(index=i,status='complete',best_step=r['best_step'],strict_gain=r['new_candidate_selected'],validation_ranking=list(ranking(v)),checkpoint_sha256=r['best_checkpoint_sha256'],regression_retained=reg.get('retention_passed') if reg else None,postprocessing_exit=t['postprocessing_exit_code']))
    candidates=[r for r in rows if r.get('strict_gain')]
    winner=max(candidates,key=lambda r:(tuple(r['validation_ranking']),-r['index'])) if complete and candidates else None
    result=dict(status='provisional-validation-comparison-awaiting-independent-local-audit' if complete else 'incomplete-batch-inspect-failures-before-selection',trials=rows,validation_only_winner_index=winner['index'] if winner else None,ranking_frozen_before_using_regression=True,independent_CPU_rescore_and_tensor_audit_required=True,production_adoption=False,independent_fresh_test_available=False,strict_export_hold_from_previous_model_not_waived=True)
    with (retrieval/'batch-comparison.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--retrieval',type=Path,required=True);compare(ap.parse_args().retrieval)
