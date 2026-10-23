"""Independent photo-max scope/trace audit, boundary packet and final research handoff."""
import json,hashlib,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation');O=R/'outputs'
D=O/'train-photo-max-loss-7870268-20261022-v1';P=O/'train-discrimination-full-query-7870268-20261022-v1';S=O/'train-discrimination-7870268-20261022-v1';B=O/'fresh-selector-batch-20261022-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,t):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(t)
def main():
    plan=read(D/'PLAN.json');report=read(D/'REPORT.json');metrics=read(D/'INDEPENDENT_AUDIT.json');parent_plan=read(P/'PLAN_V3.json')
    assert report['fits']==8 and report['total_updates']==1280 and report['seconds']<1800
    assert sha(O/'train_photo_max_loss_7870268.py')==plan['source']['script_sha256']
    assert plan['features_ref']==parent_plan['features_ref'] and plan['frozen_fitting_normalization']==parent_plan['frozen_fitting_normalization']
    assert sha(D/'FOLDS.json')==sha(P/'FOLDS_V2.json')
    assignments={r['image_id']:r for r in read(D/'TRAIN_ASSIGNMENTS.json')};traces=[];comparisons=[]
    for ref in report['result_refs']:
        assert sha(Path(ref['path']))==ref['sha256'];row=read(Path(ref['path']));fold=row['fold'];kind=row['model']
        control_ref=plan['bce_controls'][f'{fold}-{kind}'];assert sha(Path(control_ref['path']))==control_ref['sha256'];control=read(Path(control_ref['path']))
        assert row['normalization']==control['normalization']==plan['frozen_fitting_normalization'][str(fold)]
        t=row['train_prediction_trace'];cal=row['calibration'];ids=t['image_ids'];labels=t['labels'];weights=t['positive_query_loss_weights']
        pos={i for i,y in zip(ids,labels) if y};neg=set(ids)-pos
        assert cal['photo_ids']==sorted(neg) and t['negative_aggregation']=='softplus(max300logits)'
        assert math.isclose(t['negative_photo_mass'],.5/len(neg),rel_tol=1e-12)
        lookup={};positive_hits=0;positive_count=0;positive_mass=0
        for score,y,i,q,w in zip(t['scores'],labels,ids,t['query_indices'],weights):
            assert (i,q) not in lookup;lookup[i,q]=score
            if y:
                assert math.isclose(w,.5/len(pos)/len(assignments[i]['positive_queries']),rel_tol=1e-6)
                positive_mass+=w;positive_count+=1;positive_hits+=score>=.5
            else:assert w==0
        assert abs(positive_mass-.5)<1e-6
        alarms=0;query_alarms=0;max_difference=0
        for iid,scores,maximum,active in zip(cal['photo_ids'],cal['full_query_scores'],cal['per_photo_max'],t['final_active_max_queries']):
            assert len(scores)==300 and max(scores)==maximum
            assert {q for i,q in lookup if i==iid}==set(range(300))
            train_scores=[lookup[iid,q] for q in range(300)];assert train_scores[active]==max(train_scores)
            max_difference=max(max_difference,max(abs(s-v) for s,v in zip(scores,train_scores)))
            alarms+=maximum>=.5;query_alarms+=sum(s>=.5 for s in scores)
        assert max_difference<1e-5
        assert math.isclose(row['training_positive_query_recall_at_0_5'],positive_hits/positive_count,abs_tol=1e-6)
        traces.append(dict(fold=fold,model=kind,fitting_positive_hits=positive_hits,fitting_positive_queries=positive_count,
            fitting_absent_photos=len(neg),fitting_absent_photos_alarmed_at0_5=alarms,fitting_negative_query_alarms_at0_5=query_alarms,
            maximum_negative_probability=cal['maximum_negative_score'],all300_negative_queries_enter_max=True,
            final_active_query_audited=True,maximum_train_calibration_delta=max_difference))
        candidate=row['held_TRAIN_fold_training_zero_alarm'];baseline=control['held_TRAIN_fold_training_zero_alarm']
        comparisons.append(dict(fold=fold,model=kind,positive_hit_delta=candidate['positive_hits']-baseline['positive_hits'],absent_photo_alarm_delta=candidate['absent_photos_with_alarm']-baseline['absent_photos_with_alarm'],AP_delta=candidate['query_average_precision']-baseline['query_average_precision']))
    comparison_key=lambda x:(x['model'],x['fold'])
    assert sorted(comparisons,key=comparison_key)==sorted(report['objective_vs_BCE_comparisons'],key=comparison_key)
    supported=[]
    for method in ['linear','mlp32']:
        rows=[x for x in comparisons if x['model']==method]
        if all(x['positive_hit_delta']>=0 and x['absent_photo_alarm_delta']<=0 for x in rows) and any(x['positive_hit_delta']>0 or x['absent_photo_alarm_delta']<0 for x in rows):supported.append(method)
    assert supported==report['objective_clean_support_methods']==[]
    trace_doc=dict(status='photo-objective-traces-weighting-controls-and-paired-support-independently-audited',records=traces,comparisons=comparisons,
        supported_methods=supported,held_data_used_for_thresholds=False,new_fits_by_audit=0,models_saved=False,production_adoption=False)
    new(D/'OBJECTIVE_TRACE_AUDIT.json',json.dumps(trace_doc,indent=2)+'\n')
    # Review packet is TRAIN only, illustrative and selected for boundary clarity.
    records={r['image_id']:r for r in read(O/'fresh-paired-controls-20261021-v1/INPUTS.json')['records'] if r['row']['split']=='train'}
    selected=[('0c39f6a763ce3ec0','Current scope: absent','Restaurant identity sign'),('37c1b3a6b5c824d4','Current scope: absent','Business name / drive-through sign'),('757556fbf9393cff','Current scope: absent','Museum identity / directional sign'),('5a1cea0bb9f7b721','Current scope: positive','Museum exhibition advertising panel'),('13909d11dbe65be8','Current scope: positive','Advertisement behind transit display'),('20a3a8cd5733db8c','Current scope: absent','Bus-stop information board')]
    packet=[];sheet=Image.new('RGB',(1500,1110),'#f7f7f7');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',19)
    draw.text((15,12),'FrameTrail TRAIN-only boundary review: existing scopes, no predictions',font=font,fill='#111111')
    draw.text((15,42),'Review applies to future study design. Existing labels, results and TEST remain frozen.',font=font,fill='#444444')
    for index,(iid,label,caption) in enumerate(selected):
        r=records[iid];row=r['row'];path=Path(r['base'])/row['source_path'];assert sha(path)==row['image_sha256']
        item=dict(image_id=iid,source_path=str(path),image_sha256=row['image_sha256'],current_billboard_scope=row['scope']['133'],targets=[x for x in row['targets'] if x['canonical_id']==133],caption=caption)
        packet.append(item);left=(index%3)*500+10;top=90+(index//3)*505
        draw.text((left,top),iid,font=font,fill='#111111');draw.text((left,top+27),label,font=font,fill='#111111');draw.text((left,top+54),caption,font=font,fill='#444444')
        with Image.open(path) as image:
            photo=image.convert('RGB');photo.thumbnail((480,395))
        sheet.paste(photo,(left+(480-photo.width)//2,top+90))
    sheet.save(D/'BOUNDARY_REVIEW.jpg',quality=94)
    new(D/'BOUNDARY_REVIEW_PACKET.json',json.dumps(dict(status='unreviewed-by-independent-human',selection='Six illustrative TRAIN-only strict-boundary examples; not representative and not a new label release.',photos=packet,
        existing_labels_unchanged=True,test_images_used=0,purpose='Independent product/domain review for the next data/representation strategy, not retroactive rescoring.'),indent=2)+'\n')
    review=['# Six-example TRAIN-only boundary review','','The current task is large physical advertising boards, with traffic/information signs and shop/business lettering distinguished. All existing labels and scientific results remain frozen. These examples were selected from known TRAIN contexts, not as a representative sample. No predictions or scores are shown.','','Please review the originals and state whether the narrow distinctions match FrameTrail’s intended product behavior, especially business identity signs versus exhibition advertisements. Corrections would inform a future data/representation plan; they must not retroactively improve the completed validation results. This is a human/domain review request, not a claim that the existing labels are wrong.','','![Six TRAIN examples]('+str(D/'BOUNDARY_REVIEW.jpg')+')','']
    for item in packet:review+=[f"- {item['image_id']}: {item['caption']}; current scope `{item['current_billboard_scope']}`. [Original]({item['source_path']})"]
    new(D/'BOUNDARY_REVIEW_PACKET.md','\n'.join(review)+'\n')
    lines=['# Photo-level loss study: fitting task solved; held-scene clean gain still fails','','22 October 2026. The user separately authorized this eight-fit objective study. All eight fits/1280 updates completed; timed load/fit/integrity work10.406seconds, below1800seconds. No extra fits, GPU jobs, image inference, validation/TEST caches, detector retraining, model saves, exports or app changes.','','## Practical result','','The nonlinear probe fits every selected fitting positive query above0.5 and every fitting absent-photo query below0.5 in all four folds. Its highest fitting-negative probabilities are0.0278–0.0416. The capacity and objective are therefore sufficient to fit this particular query task. This does not establish full-image detector fit or sufficient data/representation generalization.','','On held TRAIN folds the nonlinear probe still alarms on15/77 absent photos at the fixed0.5 probe cutoff while recovering48/71 known positive queries. The previous full-query BCE probe recovered51/71 with20/77 alarmed photos at0.5: fewer alarms now come with fewer hits. No clean paired support is established.','','The frozen fitting-only zero-alarm thresholds fall to roughly0.03 because fitting negatives are suppressed. Applying those locked thresholds to held photos recovers63/71 positive queries but alarms on29/77 absent photos. These are uncalibrated binary-probe scores, not app detector thresholds. Do not deploy or reinterpret them as detector accuracy.','','## All held TRAIN diagnostic results','','| Objective / probe | Mean fold query AP | Hits at0.5 /71 | Absent photos alarmed at0.5 /77 | Hits at fitting-zero-alarm cutoff /71 | Absent photos alarmed there /77 |','| --- | --- | --- | --- | --- | --- |']
    for source,label in [(read(P/'INDEPENDENT_AUDIT.json'),'Query-average BCE'),(metrics,'Photo-max')]:
        for model in ['linear','mlp32']:
            a=source['aggregate'][model];lines.append(f"| {label} / {model} | {a['mean_fold_AP']:.4f} | {a['fixed_hits']} | {a['fixed_alarm_photos']} | {a['zero_hits']} | {a['zero_alarm_photos']} |")
    lines+=['','## Frozen decision and audits','','Neither architecture has nondecreasing held hits with nonincreasing absent-photo alarms in all four paired folds against its frozen BCE control. `objective_clean_support_methods=[]`. Query AP is descriptive for this objective comparison; it was not substituted for the count criterion after observing outcomes. No architecture or candidate was selected.','','Independent audits recomputed query AP/counts, calibration thresholds, recorded scene/identity separation, full query inclusion, positive weights, negative photo mass, final active-max queries, identical source folds/normalization, BCE references and source/cache hashes. All eight records and traces passed. Source model checkpoint, roles, annotations and scientific gates remain unchanged.','','## What this changes','','The current evidence no longer supports missing negative-query coverage or inability to fit TRAIN as the sole explanation. It shows a transfer/generalization problem under the fixed TRAIN folds. It does not distinguish limited scene/semantic supervision from frozen feature limitations, and does not prove annotation correctness or a unique causal explanation. Old cross-author scene exhaustiveness is not established. Selected positive queries condition on baseline geometry, other classes/NMS are absent, and these are reused development folds.','','The completed detector experiment7870268 still has no qualifying checkpoint, TESTphotos0 and production_adoption=false. Both prior eight-fit studies remain preserved. This third authorized study brings the total to24 diagnostic fits/3840 probe updates across three separately approved scopes, with no deployment models saved.','','## Next project step','','Stop automatic classifier/query/loss grids as declared. Before choosing more data versus broader feature adaptation, obtain an independent product/domain review of the six-example TRAIN boundary packet. The distinction between business identity signs, information boards and actual advertising panels governs the next supervision plan; it must not be changed merely to improve these scores. No new annotation release or fit has been made.','','The review packet supplies original paths/hashes and current scopes, without predictions. It is illustrative, unblinded to existing labels and not representative. Existing frozen labels/results cannot be retroactively changed. After this human input, prepare one bounded data/representation strategy rather than another automatic fit.','','Evidence: REPORT.json, INDEPENDENT_AUDIT.json, OBJECTIVE_TRACE_AUDIT.json, PLAN.json, AUTHORIZATION.json, BOUNDARY_REVIEW_PACKET.md and all per-fit traces.','']
    new(D/'STUDY_REPORT.md','\n'.join(lines))
    receipt=dict(status='authorized-photo-loss-study-audits-and-next-review-packet-complete',fits=8,updates=1280,objective_clean_support_methods=[],
        total_three_authorized_studies_fits=24,total_probe_updates=3840,all_MLP_fitting_queries_clean_at0_5=True,
        production_adoption=False,models_saved=False,validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,new_cluster_jobs=0,
        next_input='Independent human/product review of six frozen TRAIN scope examples for the next data/representation plan; no additional automatic fits.',
        prior_receipts={str(p):sha(p) for p in [P/'COMPLETION_RECEIPT.json',S/'COMPLETION_RECEIPT.json',B/'COMPLETION_RECEIPT_7870268.json']},
        refs=[dict(path=str(D/n),sha256=sha(D/n)) for n in ['AUTHORIZATION.json','PLAN.json','REPORT.json','INDEPENDENT_AUDIT.json','OBJECTIVE_TRACE_AUDIT.json','STUDY_REPORT.md','BOUNDARY_REVIEW_PACKET.md','BOUNDARY_REVIEW_PACKET.json','BOUNDARY_REVIEW.jpg']])
    new(D/'COMPLETION_RECEIPT.json',json.dumps(receipt,indent=2)+'\n')
    latest='''# FrameTrail:7870268 and all three authorized TRAIN studies complete; human boundary review next

LATEST22October2026: user separately approved “Run the eight-fit photo-level loss study (recommended).” It is NOWCOMPLETE, as are the prior64-query and300-query studies and detector7870268CPUevaluation. No process/session/automation running. No furtherfit/job/model/appchange started. Total3separatelyauthorizedstudies=24fits/3840diagnosticupdates; each8fits/160updates/2CPUthreads/1800scap, completedtimedphases5.187s/8.672s/10.406s.0VAL/TESTcachereads,0newimageinference,0GPU/newjobs,0models saved/selected/exported. Currentproduction_adoption=false.

Currentlastfolder outputs/train-photo-max-loss-7870268-20261022-v1. Read STUDY_REPORT.md,COMPLETION_RECEIPT.json,INDEPENDENT_AUDIT.json,OBJECTIVE_TRACE_AUDIT.json,PLAN.json,AUTHORIZATION.json,BOUNDARY_REVIEW_PACKET.md. Exactauthreceipts preserveall3userchoices; oldpendingscope paragraphs arehistorical. Actualphoto-maxstudy reused same122TRAINphotos=45positive/71baselinegeometry-coveredqueries+77wholephotoabsent, same4recordedscene/identityfolds/features/frozenparentTRAINnormalization/models/seed17/AdamW.003/wd.0001/160updates. Negativeloss=meanacrossabsentphotos softplus(max300logits);positives=meanperphoto softplus(-knownpositive logits);classmass.5/.5. PriorfullqueryBCEcontrols reused,notrefit. No coefficient sweep.

RESULT: nonlinearphoto-maxprobe fitsALLselectedfittingpositivequeries andALLfittingabsentqueries cleanlyatbinary0.5inall4folds; highestfittingnegprob.0278-.0416. Capacity/optimizationcanfitthisTRAINquerytask;notfullimagedetectorfit. HeldTRAINfolds at0.5:MLP48/71positivehits,15/77absentphotosalarmed;linear70/71,44/77. PriorfullqueryBCEMLP51/71,20/77. Loweralarmscostrecall;notcleangain. Atthresholdlockedstrictlyabovefittingnegativesonly:photoMLP63/71hits,29/77alarmed;linear38/71,8/77. QueryAPmeanphotoMLP.7160020/linear.7047109. Noappthresholdclaim. PRIMARYfrozenobjectivevsBCEpairedrulefailsbothmethods:objective_clean_support_methods=[]. Noarchitecture/model selected. All8metric,threshold,scope,sourcehash,positiveweight/negativephotomass/all300query/finalactive-max/normalization/BCEreferenceauditspass.

Inference: missingnegativequerycoverageandfailuretofitTRAINcannotsolelyexplainthiscontrolresult. Heldscene/identitygeneralization remains. Cannotuniquelyattributecausetolabels,data/scenecoverage,frozenfeaturesoroptimization. Allprobe metricsconditionedonbaselinecoveredpositivequeries,excludeotherclasses/NMS,andreuseTRAINdevelopmentfolds. Recordedscene/identitylinksdisjointincludingtransitiveoldTimesSquare,notexhaustiveoldcrossauthorsceneclearance. Noannotations/scopes/roleschanged;unknownclassesneverbackground.

DECLAREDSTOP: nofurtherautomaticclassifier/query/lossgrids afterthisscope. Bestnextprojectstepis independenthuman/productreview of6TRAINscopeexamples in BOUNDARY_REVIEW_PACKET.md/JPG/JSON beforechoosinglargersupervisiondata vsbroaderfeatureadaptation. Itshows originalphotos/currentfrozenlabels/nopredictions:freestandingrestaurantidentitysign,business/drive-throughsign,museumidentitysign vsmuseumexhibitionadvertisement,advertisementbehindtransitdisplay,bus-stopinformationboard. Selectedforillustration,notrepresentative;reviewunblindedtoexistinglabels. ThisisnotclaimthatlabelsarewrongandnotpermissiontorelabelcompletedVAL/TESTorretroactivelyrescore. Human/productinput neededfornextdata/representationdirection; no newscientificfitprepared/submitted beyondcompletedscopes. Do not turnhumanreview intoa fabricated waived gate; explain itsdecisionpurpose andlimits plainly.

Prior detector7870268evaluationcompleteonce:all4conditions/noqualifyingcheckpoint/winnernull/TEST0. M1final12TP8FP/13TP7FP;M0final11TP8FP/10TP8FP onfreshVAL14targets. Lateoldunscored542/538M1,538/538M0 exceedcap530;gainstatesaddfreshFPand1oldreviewedbillboardFP. Nootherclassmetrictriggeredrecordedretentionfailures. UnscorednotautomaticallyFP. CombinedM1train+VAL1071.375397/1063.400694s<1800.24records/6000updatesaudited. Fixed-finalTRAINdetectorgeometry38/38and37/38fresh yetsemantic/signalarms;23TRAINerrorphotos/3sheetsinspected. Allunder outputs/fresh-selector-batch-20261022-v1. No reretrieve/retrain/resubmit/reseal, no winner/TESTlock/knownregression/freshTESTinference. StartingcheckpointSHA c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 unchanged.

Prior64querystudyfolder outputs/train-discrimination-7870268-20261022-v1:PLAN_V2/FOLDS_V2actual;initialmetadata-onlybalancecorrectedbeforefits,originalpreserved. MeanAPlinear.6391273/MLP.6848929;fixed0.5hits68/71vs51/71;alarms77/77vs21/77. Fittingzeroalarmcriterion18/71vs22/71hits,4/77vs6/77alarmed. Prior300querystudy outputs/train-discrimination-full-query-7870268-20261022-v1:PLAN_V3actuallockedparentnorm,all300negatives,halfphotomass32hard/half268rest. MeanAPlinear.4990631/MLP.6908005;fixed0.5hits68/71vs51/71;alarms77/77vs20/77. Fittingzeroalarm1/71vs22/71hits,2/77vs5/77alarmed. Bothcleansupportfalse;allnegativeerrorssupervisedin300control. Frozenreceipts preserved.

Canonical C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation. SavedprojectunrelatedMiniERP—nevereditit. AppunchangedYOLOX-Sdefault/RF7805570step100explicitpreview/ONNXhold/production_adoptionfalse. StrictlyignoreCarringtonEvent/allotherprojectsfiles/jobs/logs/results/environments/sessions;onlyreceipt-verifiedFrameTrailIDs/paths. RenewedSSHkey-onlyverifiedprecedingchat,noneusedhere. Neverrequestpastedcredentials. ReadAGENTS.md/preservecontinuouslocalauthorization/batching/pairedseeds/bothbaselines/cap530/budgets/modelinvariance/validation-onlyselection/lockedwinnerTESTveto/noautomaticretries. EndeveryresponsewithsingleconcretenextFrameTrailstepandwhy;ordinarylanguage. Schedulessealedafterbaselinebeforefits;assistantreviewedprivatecohortnotindependenthumanannotation. Allhistoricalapprovals/receiptsretained.

Next step: review the six-example TRAIN boundary packet independently, because the query task now fits TRAIN cleanly but does not transfer cleanly to other scenes, and the next data/representation plan needs product-level boundary confirmation.
'''
    new(R/'NEXT_CHAT_PHOTO_LOSS_7870268.md',latest)
    for name in ['CURRENT_HANDOFF.md','NEXT_CHAT_7870268_EVALUATED.md','NEXT_CHAT_DISCRIMINATION_7870268.md','NEXT_CHAT_FULL_QUERY_7870268.md']:
        p=R/name;old=p.read_text(encoding='utf-8-sig');p.write_text(latest+'\n---\n\n# Preserved prior handoff\n\n'+old,encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],supported_methods=supported,fit_traces=traces,report=str(D/'STUDY_REPORT.md'),review_packet=str(D/'BOUNDARY_REVIEW_PACKET.md')),indent=2))
if __name__=='__main__':main()
