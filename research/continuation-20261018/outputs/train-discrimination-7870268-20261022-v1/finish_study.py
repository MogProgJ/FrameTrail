"""Document completed scope and concrete unexecuted follow-up; preserve receipts."""
import json,hashlib
from pathlib import Path
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
D=R/'outputs/train-discrimination-7870268-20261022-v1'
B=R/'outputs/fresh-selector-batch-20261022-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,text):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
def main():
    a=read(D/'INDEPENDENT_AUDIT.json');report=read(D/'REPORT.json');plan=read(D/'PLAN_V2.json')
    assert not a['nonlinear_consistent_support'] and report['fits']==8
    summary='''# TRAIN-only discrimination study: eight fits complete

22 October 2026. The user explicitly chose “Run the separate TRAIN-only discrimination study (recommended)” after the completed detector experiment had no qualifying model. AUTHORIZATION.json preserves this separate scope; it supersedes the earlier pending-scope text for this study only. No detector retraining or cluster job occurred.

The small nonlinear probe improved mean query ranking but did not provide a consistent clean operating advantage. It failed the rule frozen before fitting. No architecture or model was selected, retained, exported or installed.

## Design and execution

-124 existing TRAIN photos inspected through pinned cached features only.122 participate:45 positive photos with71 one-to-one geometry-covered positive queries, plus77 whole-photo absent photos. Two old positives have no covered query and are explicitly excluded, not relabeled negative.
-Four folds keep every recorded identity/scene component together, including transitive old Times Square links. Old cross-author scene exhaustiveness is not claimed. All four held folds contain fresh positives.
-The initial metadata-only preparation put no fresh positive in fold0. That preparation and its hashes remain preserved. PLAN_V2.json/FOLDS_V2.json repaired balance before any fit or fit prediction. These are the actual frozen fit inputs.
-Linear256→1 and nonlinear256→32→1 probes,160 fixed updates each, eight fits/1280 diagnostic updates total, two CPU threads, AdamW lr0.003/wd0.0001, initialization17. Same prior-probe settings; fitting-fold-only normalization and equal class/photo mass.
-Only32 baseline-hard plus32 evenly spaced other negative queries per fitting absent photo. All300 queries are scored on held absent photos and for fitting-fold calibration. Unmatched positive-photo queries remain excluded, including unknown old partial scopes. No unknown class becomes background.
-Fixed0.5 probe scores retained for comparison. A second threshold is locked separately per fit strictly above the highest score across all300 queries of fitting-fold absent photos, before held-fold scoring. It is never calibrated on held scores and is not an app confidence threshold.
-Timed fitting/load/final integrity phase5.187seconds, well below1800seconds. Runtime startup/preparation are separate. No retries, extensions or extra fits. Source/cache hashes unchanged. No validation/TEST cache reads, new image inference, GPU use or model files.

## Independently recomputed results

| Probe | Mean fold query AP | Held hits at0.5 /71 | Held absent photos alarmed at0.5 /77 | Held hits at TRAIN-zero-alarm criterion /71 | Held absent photos alarmed at that criterion /77 |
| --- | --- | --- | --- | --- | --- |
'''
    for model,label in [('linear','Linear'),('mlp32','Nonlinear32')]:
        x=a['aggregate'][model];summary+=f"| {label} | {x['mean_fold_AP']:.4f} | {x['fixed_hits']} | {x['fixed_alarm_photos']} | {x['zero_hits']} | {x['zero_alarm_photos']} |\n"
    summary+='''
The nonlinear probe improves query AP in three of four folds but worsens it by0.0400 in fold1. At the fitting-fold zero-alarm criterion, fold2 gains two hits while adding alarms on three more absent photos. Fold3 gains two hits and removes one alarm; folds0/1 have the same operating hit/alarm counts. The predefined all-four-fold non-worsening rule fails. Mean ranking improvement alone does not satisfy it.

At0.5, lower nonlinear alarm counts also come with lower positive recovery. The pooled query/photo results are descriptive TRAIN diagnostics conditioned on frozen box coverage, not detector recall, mAP, app false-alarm rates or independent test accuracy. There is no NMS/other-class competition in these binary probes.

## Remaining uncertainty

The nonlinear sampled training loss is about0.0031–0.0037, but evaluating all300 queries on its own fitting absent photos finds alarms on5–8 photos per fit. Each fit supervised only64/300 queries per absent photo. This makes negative-query coverage a concrete next variable to control. The retained per-photo maxima do not establish whether individual alarms came from sampled or omitted queries; do not claim omission caused the errors. Rare sampled errors, weighting/optimization and generalization may also explain them.

The diagnostic supports neither “a bigger head solves it” nor “frozen features can never work.” The current row-only detector recipe stays closed, and the starting model stays unchanged. Fresh TEST remains unused.

Next step: resolve the separate full-negative-query coverage control described in FULL_QUERY_CONTROL_PROPOSAL.md, because the completed eight-fit scope cannot distinguish incomplete query supervision from discrimination failure across all fitting negatives.
'''
    new(D/'STUDY_REPORT.md',summary)
    proposal='''# Separate full-negative-query coverage control: proposed, not run

The completed authorized scope was eight fits total. This control would add eight, so it requires a separate scope decision. It is not a retry, replacement or extra update of a completed fit. No fit, upload or job has been started for this proposal.

Question: does supervising every fitting absent-photo query reduce the residual alarms, or does the problem persist with complete query coverage?

Exact proposed matrix: the same four frozen scene/identity folds crossed with the same linear and32-unit nonlinear probes,160 updates per fit,1280 updates total. Use the same pinned initial TRAIN features, positive query assignments, seed17, AdamW lr0.003/wd0.0001, fitting-only normalization, equal class/photo mass, fixed0.5 metrics and fitting-fold zero-alarm threshold. Reuse PLAN_V2/FOLDS_V2 and all existing input hashes. No additional model/optimizer/threshold sweep, selection or deployment.

Single intended treatment: replace the32 evenly spaced non-hard negative samples with all268 non-hard queries. Retain the32 baseline-hard queries. Within each absent photo preserve half of its mass for the32 hard queries and half for the remaining268, matching the original hard-versus-other weighting. This replaces the sampled estimate of the other-query term with complete coverage while preserving class/photo mass and hard-negative emphasis. Document that equivalence and validate weights before fitting.

Save full fitting-negative query scores and query indices, per-photo alarms and the largest violating queries. This instrumentation must distinguish residual fitting errors from omitted-query errors; save prediction traces only, no fitted model files. Audit all metrics and fitting-only threshold selection independently.

Resources: sequential CPU only, two threads, total timed active cap1800seconds, no GPUs/cluster jobs. Eight fits maximum, no retries/replacements/budget extensions. No validation or TEST images/caches, no new photo inference, no data/annotation edits, no source-checkpoint or app changes. Existing detector qualification, both baselines, cap530 and locked-winner TEST rules remain intact; this diagnostic cannot promote a model.

Predeclared interpretation: compare paired fold metrics and fitting-photo alarms with the completed64-query study. A lower sampled/full loss is insufficient; seek consistent held-fold recovery without extra absent-photo alarms. No threshold tuning on held-fold scores. These are reused TRAIN development folds, not fresh validation/test evidence. If complete coverage still fails, preserve that result and stop automatic query-sampling/capacity fits; prepare a distinct supervision/loss/representation study before new training.

Next step: choose whether to run this separate eight-fit coverage control, because it directly tests the remaining query-coverage uncertainty within a small fixed CPU budget.
'''
    new(D/'FULL_QUERY_CONTROL_PROPOSAL.md',proposal)
    receipt=dict(status='eight-fit-study-and-independent-audit-complete',fits=8,updates=1280,consistent_nonlinear_support=False,
        validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,new_cluster_jobs=0,models_saved=False,production_adoption=False,
        next_scope='Separate eight-fit full-negative-query coverage control proposed; not run',
        refs=[dict(path=str(D/n),sha256=sha(D/n)) for n in ['AUTHORIZATION.json','PLAN_V2.json','FOLDS_V2.json','REPORT.json','INDEPENDENT_AUDIT.json','STUDY_REPORT.md','FULL_QUERY_CONTROL_PROPOSAL.md']],
        prior_experiment_completion_sha256=sha(B/'COMPLETION_RECEIPT_7870268.json'))
    new(D/'COMPLETION_RECEIPT.json',json.dumps(receipt,indent=2)+'\n')
    latest='''# FrameTrail: detector experiment and authorized discrimination study complete

LATEST22October2026: detector7870268 CPUevaluation completed once; all four scientific conditions complete, no qualifying checkpoint, winner=null, TESTphotos0, production_adoption=false. M1final12TP8FP/13TP7FP onfreshVAL14targets; M0final11TP8FP/10TP8FP. Frozen known-class/unknown-cap530 gates preserved; late unknowncounts542/538 M1 and538/538 M0. Existing exact-step qualification/record audit passed24records and6000updates. Startingmodel c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 unchanged. No reretrieve/retrain/resubmit/reseal. No winner/TESTlock or inference.

User then explicitly chose: “Run the separate TRAIN-only discrimination study (recommended).” That eight-fit CPU study is NOW COMPLETE, not pending authorization. AUTHORIZATION.json under outputs/train-discrimination-7870268-20261022-v1 preserves separate provenance. Exactly8fits/1280diagnosticupdates,2CPUthreads,5.187stimedfit/load/integrityphase,0VAL/TESTcachereads,0imageinference,0GPU/newjobs,0models saved. Sources/checkpoint/caches unchanged. No process/session/automation running.

Actualfrozeninputs PLAN_V2.json/FOLDS_V2.json:122participatingTRAINphotos=45positive/71geometry-coveredpositivequeries+77reviewedabsent.2oldpositivephotos geometry-uncovered excluded. Transitive recordedscene+identity components kept together, includingoldTimesSquare. Everyfold has fresh positives. Initial metadata-only PLAN/FOLDS preserved; corrected beforefits because fold0hadnofreshpositive. Oldcross-author sceneexhaustiveness notclaimed.64negativequeries/photo (32baselinehard+32other), all300evaluated. Linear vsMLP32,4folds,160updates,AdamW.003/wd.0001,seed17,fit-onlynormalization,equalclass/photo mass. Otherclassesunknown, unmatchedpartialpositivequeriesnotnegative.

Independent plainPythonmetric/threshold/fold/source audit passedall8. MeanqueryAP linear.6391273,MLP.6848929 (MLPbetter3/4folds,worsefold1). Atfixedbinary0.5:68/71vs51/71positivequeries;77/77vs21/77absentphotosalarmed. Atthresholdchosenstrictlyaboveeveryfittingnegativequeryscore:18/71vs22/71hits;4/77vs6/77absentphotosalarmed. MLPfailsfrozenall4foldnonworseningrule (fold1APworse;fold2+2hits,+3alarmedphotos). Noarchitecture/model selected. TheseareTRAINquerydiagnostics,notdetector/appaccuracy;noclaimstatisticalindependence.

Residualquestion: MLPsampledTRAINloss.0031-.0037 yetall300querychecks alarmon5–8fittingabsentphotos/fold. Only64queriesenteredfit. Savedmaxima donotprovealarmsbelongtoomittedqueries; donotclaimcausality. Concrete separate follow-up prepared: FULL_QUERY_CONTROL_PROPOSAL.md adds8fits on samefolds/features, replacing32samplednonhardqueries withall268, preserving50/50hard/restweighting,class/photo mass,160updates and1800s2CPUcap. Fullnegativequeryscoretraces;0VAL/TEST/GPU/modeladoption. NOTRUN. Requires separate scope decision because approved8fitsarecomplete; donot automatically exceedfitcount. No needforSSH/credentials.

Read outputs/train-discrimination-7870268-20261022-v1/{STUDY_REPORT.md,COMPLETION_RECEIPT.json,INDEPENDENT_AUDIT.json,FULL_QUERY_CONTROL_PROPOSAL.md}. Detectorreport/receipts remain under outputs/fresh-selector-batch-20261022-v1. Fixed-finalTRAINdetector diagnosis and23photo/3sheetinspection are complete there; no label/scope/split changes. No moreexports/appqualification warranted withoutaqualifiedmodel.

Canonicalfolder C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation; savedprojectpointsunrelatedMiniERP—nevereditit. App unchanged YOLOX-Sdefault/RF7805570step100explicitpreview/ONNXhold/production_adoption=false. StrictlyignoreCarringtonEvent/allotherprojectsfiles/jobs/logs/results/environments/sessions. Onlyreceipt-verifiedFrameTrailIDs/paths permitted. Renewedkey-onlySSHverifiedprecedingchat; none neededhere. Neverrequestpastedcredentials. ReadAGENTS.md;preservecontinuousauthorization,batching,pairedseeds,bothbaselines,cap530,budgets,modelinvariance,validation-onlyselection,lockedwinnerTESTveto,noretries/replacements. User-facingplainlanguage;end everyresponsewithsingleconcretenextFrameTrailstepandwhy. Scheduleimplementationsealedafterbaselinebeforefits;keepthatlimitation.

Next step: resolve the separate full-negative-query coverage control scope, because the completed eight-fit study leaves query supervision coverage as a specific testable uncertainty.
'''
    new(R/'NEXT_CHAT_DISCRIMINATION_7870268.md',latest)
    for name in ['CURRENT_HANDOFF.md','NEXT_CHAT_7870268_EVALUATED.md']:
        path=R/name;old=path.read_text(encoding='utf-8-sig');path.write_text(latest+'\n---\n\n# Preserved previous handoff\n\n'+old,encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],report=str(D/'STUDY_REPORT.md'),proposal=str(D/'FULL_QUERY_CONTROL_PROPOSAL.md')),indent=2))
if __name__=='__main__':main()
