"""Audit complete fitting-query traces, document outcome, preserve final handoff."""
import json,hashlib,math
from pathlib import Path
ROOT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT=ROOT/'outputs';D=OUT/'train-discrimination-full-query-7870268-20261022-v1';P=OUT/'train-discrimination-7870268-20261022-v1';B=OUT/'fresh-selector-batch-20261022-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,text):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
def main():
    plan=read(D/'PLAN_V3.json');report=read(D/'REPORT.json');audit=read(D/'INDEPENDENT_AUDIT.json');old=read(P/'INDEPENDENT_AUDIT.json')
    assert not report['nonlinear_consistent_support_under_frozen_rule']
    assert plan['source']['script_sha256']==sha(OUT/'train_discrimination_full_query_7870268.py')
    assert plan['source']['parent_study_script']['sha256']==sha(OUT/'train_discrimination_study_7870268.py')
    assert sha(D/'FOLDS_V2.json')==sha(P/'FOLDS_V2.json')
    assignments={r['image_id']:r for r in read(D/'TRAIN_ASSIGNMENTS.json')}
    traces=[]
    for ref in report['result_refs']:
        assert sha(Path(ref['path']))==ref['sha256'];r=read(Path(ref['path']));fold=r['fold'];kind=r['model']
        assert r['normalization']==read(P/f'fits/fold-{fold}-{kind}.json')['normalization']==plan['frozen_fitting_normalization'][str(fold)]
        train=r['train_prediction_trace'];assert len(train['scores'])==len(train['labels'])==len(train['image_ids'])==len(train['query_indices'])==len(train['loss_weights'])
        fitting_ids=set(train['image_ids']);pos_ids={i for i in fitting_ids if assignments[i]['pool'].endswith('positive')};neg_ids=fitting_ids-pos_ids
        lookup={};mass=[0.,0.]
        for s,y,i,q,w in zip(train['scores'],train['labels'],train['image_ids'],train['query_indices'],train['loss_weights']):
            assert (i,q) not in lookup;lookup[i,q]=(s,y,w);mass[int(y)]+=w
            assert y==int(i in pos_ids)
            if y:expected=.5/len(pos_ids)/len(assignments[i]['positive_queries'])
            else:
                hard=assignments[i]['baseline_hard_queries'];expected=.5/len(neg_ids)*(.5/32 if q in hard else .5/268)
            assert math.isclose(w,expected,rel_tol=1e-6,abs_tol=1e-12)
        assert all(abs(v-.5)<1e-6 for v in mass)
        calibration=r['calibration'];assert calibration['all_fitting_negative_queries_supervised'] and calibration['query_indices']==list(range(300))
        alarms=[];hard_alarms=0;other_alarms=0;max_delta=0.;query_alarms=0
        assert set(calibration['photo_ids'])==neg_ids
        for iid,scores,maximum in zip(calibration['photo_ids'],calibration['full_query_scores'],calibration['per_photo_max']):
            assert len(scores)==300 and max(scores)==maximum
            assert {q for i,q in lookup if i==iid}==set(range(300))
            hard=set(calibration['baseline_hard_queries'][iid]);assert hard==set(assignments[iid]['baseline_hard_queries']) and len(hard)==32
            for q,s in enumerate(scores):
                training_score,y,w=lookup[iid,q];assert y==0
                max_delta=max(max_delta,abs(s-training_score))
                if s>=.5:
                    query_alarms+=1
                    if q in hard:hard_alarms+=1
                    else:other_alarms+=1
            if maximum>=.5:alarms.append(dict(image_id=iid,max_score=maximum,pool=assignments[iid]['pool']))
        assert max_delta<1e-5
        traces.append(dict(fold=fold,model=kind,fitting_absent_photos=len(neg_ids),fitting_absent_photos_alarmed_at0_5=len(alarms),
            negative_query_alarms_at0_5=query_alarms,hard_query_alarms=hard_alarms,other_query_alarms=other_alarms,
            largest_alarm_photos=sorted(alarms,key=lambda x:(-x['max_score'],x['image_id']))[:10],
            maximum_train_vs_calibration_score_difference=max_delta,all300_queries_supervised=True,hard_rest_and_class_photo_mass_passed=True))
    trace_doc=dict(status='all-eight-full-query-traces-and-single-treatment-controls-audited',records=traces,
        source_folds_and_normalization_identical=True,all_negative_queries_supervised=True,
        validation_or_test_reads=0,optimizer_updates_by_audit=0,production_adoption=False)
    new(D/'FULL_QUERY_TRACE_AUDIT.json',json.dumps(trace_doc,indent=2)+'\n')
    lines=['# Full-negative-query control: complete; no qualifying clean advantage','','22 October 2026. The user separately authorized eight additional CPU fits. Exactly eight fits/1280 diagnostic updates completed in8.672seconds of timed load/fit/integrity work, below1800seconds. No validation/TEST data, new image inference, GPU job, detector retraining, export or model adoption.','','The nonlinear probe ranks positive queries better than the linear probe in all four folds under this control. It still adds held absent-photo alarms in two folds at the fitting-fold criterion and fails the frozen clean-gain rule. Compared with its own64-query result, complete coverage provides no consistent clean improvement. Stop automatic query-sampling/capacity fits as declared.','','## Controlled treatment','','The same122 TRAIN photos,71 covered positive queries, four recorded scene/identity folds, initializations, models and160 updates were retained. Positive supervision is unchanged. All300 fitting-absent queries now enter the loss:32 unchanged baseline-hard queries share half the photo mass;268 other queries share half. Class/photo mass remains fixed.','','Before fits, exact parent fitting-fold means/stds were locked to avoid changing preprocessing with query coverage. PLAN_V3.json is authoritative; the earlier preparation/code is preserved. Independent audit verifies every query is included, exact loss weights, identical folds and normalizations, full calibration traces and fitting-only thresholds.','','## Held TRAIN-fold results','','These are binary query diagnostics on reused TRAIN development folds, not detector or app accuracy. Each threshold is locked strictly above all fitting-fold negative scores before held-fold scoring.','','| Study / probe | Mean fold query AP | Hits at0.5 /71 | Absent photos alarmed at0.5 /77 | Hits at fitting-zero-alarm criterion /71 | Absent photos alarmed at that criterion /77 |','| --- | --- | --- | --- | --- | --- |']
    for source,label in [(old,'64queries'),(audit,'300queries')]:
        for model in ['linear','mlp32']:
            a=source['aggregate'][model];lines.append(f"| {label} / {model} | {a['mean_fold_AP']:.4f} | {a['fixed_hits']} | {a['fixed_alarm_photos']} | {a['zero_hits']} | {a['zero_alarm_photos']} |")
    lines+=['','In the300-query control, nonlinear versus linear gains2/7/9/3 held hits by fold, with absent-photo alarm changes-1/+1/+3/0. This fails the predefined no-extra-alarm requirement in folds1/2. Against the previous nonlinear probe, fitting-zero-alarm hits remain22/71 and alarmed photos fall from6/77 to5/77, but the changes are not consistent across folds. Ranking gains do not establish a clean deployable operating point.','','## Fitting errors after complete supervision','','| Fold / probe | Fitting absent photos | Fitting absent photos alarmed at0.5 | Supervised negative queries alarmed | Baseline-hard / other alarm queries |','| --- | --- | --- | --- | --- |']
    for t in traces:lines.append(f"| {t['fold']} / {t['model']} | {t['fitting_absent_photos']} | {t['fitting_absent_photos_alarmed_at0_5']} | {t['negative_query_alarms_at0_5']} | {t['hard_query_alarms']} / {t['other_query_alarms']} |")
    lines+=['','The remaining fitting alarms are now known to be on supervised queries. Omitted negative queries therefore cannot fully explain these control errors. This does not prove the optimizer, loss, labels or frozen features are uniquely responsible. Low average query loss alone does not enforce a no-alarm photo criterion; rare high-confidence errors can remain under the fixed recipe.','','No new data, taxonomy, annotations, thresholds or detector gates were changed. The probe0.5 thresholds and fitting thresholds are not FrameTrail app confidence settings. Old cross-author scene exhaustiveness is not established; only recorded scene/identity links are enforced. Existing geometry conditioning and prior development history limit the inference.','','## Next research decision','','The best next hypothesis is a photo-level worst-negative objective that directly addresses each absent photo’s most confident false alarm. That is a distinct loss study, outside both completed eight-fit scopes, and has not been run. A concrete proposal is in NEXT_OBJECTIVE_STUDY_PROPOSAL.md. No further automatic query-sampling/capacity fits are warranted.','','Current detector remains the starting checkpoint. The completed detector experiment still has no eligible winner; TEST is untouched; production_adoption=false.','','Evidence: REPORT.json, INDEPENDENT_AUDIT.json, FULL_QUERY_TRACE_AUDIT.json, PLAN_V3.json, AUTHORIZATION.json and per-fit score traces.','']
    new(D/'CONTROL_REPORT.md','\n'.join(lines))
    proposal='''# Distinct next hypothesis: photo-level worst-negative loss

Prepared only. No fit, model, upload or job. Both approved eight-fit diagnostic scopes are complete; their declared automatic-fit stop rules remain in force.

Why this is the next discriminating question: full supervision of all300 fitting-negative queries did not remove all fitting-photo alarms. The nonlinear probe has low mean loss and better ranking, yet no consistent clean operating point. The current query-average loss and the product’s photo-level no-alarm requirement are different objectives. This motivates testing an objective change; it does not prove causality or justify longer training.

Concrete proposed study: reuse the same four recorded scene/identity folds,71 covered positive queries and77 absent photos, frozen baseline features, exact locked parent normalizations, linear and32-unit nonlinear probes, seed17, AdamW lr0.003/wd0.0001 and160updates. Eight new CPU fits total. Reuse the already-completed300-query BCE fits as controls; do not refit those controls.

Single loss change: each positive photo contributes the mean softplus of its negative positive-query logits; each absent photo contributes softplus of its maximum logit across all300 queries. Average each class over photos and give positive/absent classes equal0.5mass. No unmatched partial-positive query becomes negative, no unknown class becomes background, no tuneable penalty coefficient or parameter grid. Do not modify detector confidence thresholds or labels.

Retain fixed0.5 readouts and the same fitting-fold-only zero-alarm threshold, complete fitting/held query traces, weighting and numerical checks. Predeclare clean paired held-fold support before any fit; low loss or training fit cannot promote a model. These are reused TRAIN development folds, not fresh validation/test evidence. No deployable probe/model saved.

Bounds: eight fits/1280updates, two CPU threads,1800s total timed active cap, no retries/replacements/extensions. Zero validation/TEST cache reads, image inference, GPU jobs, detector changes or app adoption. All current scientific/model/data/export gates stay intact. If this also lacks consistent clean support, stop automatic loss/capacity probing and surface a broader representation/supervision strategy decision rather than starting another grid.

Scope decision needed: run this distinct objective study, or stop further RF feature-probe fits and reassess the broader model strategy. This proposal is separate from the two completed user-authorized eight-fit scopes.

Next step: resolve this photo-level loss study scope, because complete negative-query coverage leaves a specific objective-versus-criterion mismatch to test before another GPU run.
'''
    new(D/'NEXT_OBJECTIVE_STUDY_PROPOSAL.md',proposal)
    receipt=dict(status='authorized-full-query-control-and-all-audits-complete',fits=8,updates=1280,consistent_clean_support=False,
        models_saved=False,production_adoption=False,new_cluster_jobs=0,validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,
        parent_receipt_sha256=sha(P/'COMPLETION_RECEIPT.json'),detector_receipt_sha256=sha(B/'COMPLETION_RECEIPT_7870268.json'),
        next_scope='Distinct photo-level loss study proposed; not run; automatic query/capacity fitting stopped',
        refs=[dict(path=str(D/n),sha256=sha(D/n)) for n in ['AUTHORIZATION.json','PLAN_V3.json','FOLDS_V2.json','REPORT.json','INDEPENDENT_AUDIT.json','FULL_QUERY_TRACE_AUDIT.json','CONTROL_REPORT.md','NEXT_OBJECTIVE_STUDY_PROPOSAL.md']])
    new(D/'COMPLETION_RECEIPT.json',json.dumps(receipt,indent=2)+'\n')
    latest='''# FrameTrail:7870268 evaluation and both authorized TRAIN studies complete

LATEST22October2026: user explicitly approved separate full-query eight-fit control after first eight-fit study. Both scopes are NOW COMPLETE, not pending. Main detector evaluation7870268 also complete, all4conditions/noeligiblecheckpoint/winnernull/TEST0/production_adoption=false. M1final12TP8FP/13TP7FP;M0final11TP8FP/10TP8FP onfreshVAL14targets. All gates/records/schedules/frozenparameters/budgets passed audit as applicable; errors preventqualification. Startingmodel c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 unchanged; appYOLOX-Sdefault/RF7805570step100explicitpreview/ONNXhold unchanged. No reretrieve/retrain/resubmit/reseal. No winner/TESTconsumptionlock or freshTESTinference.

Both TRAINstudies: each exactly8fits/1280diagnosticupdates, linear vsMLP32,4recordedscene+identity folds,122participatingTRAINphotos (45positive/71coveredqueries+77wholephotoabsent). Two old positives geometry-uncovered excluded. OnlyTRAINfeatures,0VAL/TESTcachereads/0newimageinference/0GPU/newjobs/0modelssaved. All sources remainunchanged. Initialstudy timedphase5.187s;fullquerycontrol8.672s;each<1800s. No backgroundprocess/session/automation remains. PlainPythonmetric/threshold/fold/hash audits passed both; fullcontrol also passes exact loss-weight, all300queryinclusion, sourcefold/normalization and querytrace audits.

Firststudy (outputs/train-discrimination-7870268-20261022-v1): userapproved “Run the separate TRAIN-only discrimination study (recommended).” ActualPLAN_V2/FOLDS_V2: repaired initial metadata-only foldbalance beforefits, originalpreserved;knownTimesSquare/identitylinks transitive.64fittingnegativequeries/photo,32hard+32other. MeanqueryAP linear.6391273/MLP.6848929,MLPbetter3/4. Atbinary0.5:68/71vs51/71hits,77/77vs21/77absentphotosalarmed. Atfitting-fold-zero-alarmthreshold:18/71vs22/71hits,4/77vs6/77alarmedphotos. MLPfailedall4foldclean-support rule. Its5–8fittingabsentphotosalarmeddidnotestablishwhetherqueriesweresampled/omitted;thatuncertainty motivatedcontrol.

Fullcontrol (outputs/train-discrimination-full-query-7870268-20261022-v1): userapproved “Run the eight-fit full-query control (recommended).” ActualPLAN_V3 (earlierpreparationpreserved) usesall300negativequeries;32unchangedhardqueriesgethalfphotomass,268resthalf;class/photomass preserved. Exactparentfitting-foldmean/std locked so onlycoverage changes. Samefolds,positivequeries,160updates,seed17,AdamW.003/wd.0001. Completefitting-negative scores/queryindices/weights saved. MeanqueryAP linear.4990631/MLP.6908005;MLPbetter4/4. Atbinary0.5:68/71vs51/71hits,77/77vs20/77alarmedphotos. Atfitting-zero-alarmcriterion:1/71vs22/71hits,2/77vs5/77alarmedphotos. MLPgainshitsbutaddsalarmsinfolds1/2;frozenclean-supportfalse. Againstitself64queryMLPstill22hits,6→5alarmedphotos,notconsistentacrossfolds. Noarchitecture/modelselected.

Fulltraceauditproves remaining fitting alarms are on supervised queries; omittednegativequeriescannotfullyexplainthem. No claim that loss,optimizer,labelsorfeatures are uniquely causal. Binaryprobe thresholdsareNOTappthresholds;TRAINquerymetricsarenotdetector/appaccuracy. Recordedscene/identitylinksdisjoint;oldcrossauthorsceneexhaustiveness notclaimed. Noannotation/label/scope/split/thresholdcuration. Bothbaseline/cap530/pairedseed/lockedTEST/exportgates remain.

Read latestcontrol CONTROL_REPORT.md,COMPLETION_RECEIPT.json,INDEPENDENT_AUDIT.json,FULL_QUERY_TRACE_AUDIT.json,PLAN_V3.json,AUTHORIZATION.json. PriorstudySTUDY_REPORT andoriginaldetectorPOSTRUN_REPORT remainhistoricalverifiedevidence. Original23TRAINdetectorerrorphotos/3sheetsinspected;notanexhaustiveneworiginalannotationaudit.

DECLAREDSTOP: no further automatic query-sampling/capacity fits. Concrete distinct objective proposal prepared at latestcontrol/NEXT_OBJECTIVE_STUDY_PROPOSAL.md:8newCPUfits,reuseBCEcontrols,samefolds/features/norm/settings,negativephoto loss=softplus(max300logits),positivephoto loss=meanpositive softplus,50/50classmass,160updates/1800s2CPUcap.0VAL/TEST/GPU/modeladoption. NOTRUN. Requires separate scientific scope choice; do not silently exceed completed8-fit bounds or start another grid. No SSH/credentials needed. Latestexplicitauthorization covers completedfullquerycontrol,notthisnewlossstudy.

Canonicalfolder C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation; savedproject unrelatedMiniERP—nevereditMiniERP. StrictlyignoreCarringtonEvent/allotherprojectsfiles/jobs/logs/results/environments/sessions. Onlyreceipt-verifiedFrameTrailIDs/paths. RenewedSSHkey-onlyverifiedprecedingchat;noneusedhere. Neverrequestpastedcredentials. ReadAGENTS.md/preservecontinuousworkauthorization/batching/scientificbounds/noautomaticretries. EndeveryresponsewithsingleconcretenextFrameTrailstepandwhy;ordinarylanguage. Honestexecutionorder schedulessealedafterbaselinebeforefits,assistantreviewedprivatecohortnotindependenthumanannotation.

Next step: resolve the distinct photo-level worst-negative loss study scope, because full query coverage leaves a specific objective-versus-no-alarm mismatch to investigate before new GPU training.
'''
    new(ROOT/'NEXT_CHAT_FULL_QUERY_7870268.md',latest)
    for name in ['CURRENT_HANDOFF.md','NEXT_CHAT_7870268_EVALUATED.md','NEXT_CHAT_DISCRIMINATION_7870268.md']:
        p=ROOT/name;prior=p.read_text(encoding='utf-8-sig');p.write_text(latest+'\n---\n\n# Preserved prior handoff\n\n'+prior,encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],trace_records=traces,report=str(D/'CONTROL_REPORT.md'),next_proposal=str(D/'NEXT_OBJECTIVE_STUDY_PROPOSAL.md')),indent=2))
if __name__=='__main__':main()
