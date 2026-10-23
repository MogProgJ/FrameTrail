"""CPU contracts for a fixed four-task array; no actual model optimization."""
import copy,importlib.util,io,json,os,sys,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
identity=json.loads((HERE/'PROPOSAL_IDENTITY.json').read_text());T=HERE/identity['package_directory'];sys.path.insert(0,str(T))
import torch
from continuation_guard import inputs,approval,variant,read,sha,stop_without_gain
from selector_mechanics import configure
from preflight import preflight
from verify_package import verify
import verify_results as verifier
from regression_stage import gate
from compare_batch import compare

class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures=[inputs(T,False,i) for i in range(4)]
    def test_all_schedules_are_distinct_training_only_batches(self):
        for i,(release,schedule,_,_) in enumerate(self.fixtures):
            train={r['image_id'] for r in release['images'] if r['split']=='train'}
            n=variant(T,i)['accumulation'];self.assertEqual(len(schedule),3000)
            self.assertTrue(all(len(b)==len(set(b))==n and set(b)<=train for b in schedule))
    def test_paired_schedules_isolate_encoder_lr_and_region_weight(self):
        s=[f[1] for f in self.fixtures];self.assertTrue(all(x==s[0] for x in s))
        self.assertEqual({(v['encoder_lr'],v['region_weight']) for v in read(T/'protocol.json')['variants']},{(.00001,1),(.00001,3),(.00003,1),(.00003,3)})
        overlay=read(T/'region-review.json');self.assertEqual(len(overlay['regions']),8)
        self.assertEqual(s[0][:1500],read(HERE.parent/'selector-stage-7809335-20261018-v1/CPU_CONTROL_SCHEDULE.json'))
    def test_index_cannot_silently_default_or_escape(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):variant(T)
        for i in (-1,4,True):
            with self.assertRaises(ValueError):variant(T,i)
    def test_approval_absent_and_early_stop_fixed(self):
        with self.assertRaisesRegex(ValueError,'Explicit approval'):approval(T)
        self.assertTrue(stop_without_gain(1500,0));self.assertFalse(stop_without_gain(1500,100))
    def test_synthetic_updates_only_both_row133s(self):
        from selector_mechanics import fingerprint_frozen
        for lr in (.00001,.00003):
            net=torch.nn.Module();net.class_embed=torch.nn.Linear(4,616);net.backbone=torch.nn.Linear(4,4);net.transformer=torch.nn.Module();net.transformer.enc_out_class_embed=torch.nn.ModuleList([torch.nn.Linear(4,616)])
            opt,check,allowed=configure(net,lr);frozen=fingerprint_frozen(net,allowed);before={k:v.clone() for k,v in net.state_dict().items()}
            (net.class_embed(torch.ones(2,4)).square().sum()+net.transformer.enc_out_class_embed[0](torch.ones(2,4)).square().sum()).backward();opt.step();check()
            self.assertEqual(frozen,fingerprint_frozen(net,allowed))
            for key in allowed:self.assertFalse(torch.equal(before[key][133],net.state_dict()[key][133]))
    def test_windows_linux_sampler_serialization_and_wrong_variant(self):
        s=self.fixtures[0][1];verifier.verify_schedule(json.loads(json.dumps(s,indent=2)+'\r\n'),'123_0')
        verifier.verify_schedule(s,'123_1') # paired schedule deliberately identical
        changed=copy.deepcopy(s);changed[0][0]='wrong'
        with self.assertRaises(ValueError):verifier.verify_schedule(changed,'123_0')
    def test_safe_members_accept_array_identity_reject_traversal_and_links(self):
        class Fake:
            def __init__(self,m):self.m=m
            def getmembers(self):return self.m
        verifier.members_checked(Fake([tarfile.TarInfo('output/rf-selector-123_0/report.json')]),'123_0')
        for name in ('output/rf-selector-123_0/../../../escape','output/rf-selector-123_1/report.json'):
            with self.assertRaises(ValueError):verifier.members_checked(Fake([tarfile.TarInfo(name)]),'123_0')
        link=tarfile.TarInfo('output/rf-selector-123_0/link');link.type=tarfile.SYMTYPE
        with self.assertRaises(ValueError):verifier.members_checked(Fake([link]),'123_0')
    def test_regression_guard_detects_loss_and_fp_increase(self):
        baseline=dict(by_class={'billboard':dict(complete_tp=1,complete_fp=0,partial_positive_hits=1)})
        self.assertTrue(gate(baseline,baseline)['passed'])
        for metric,value in [('complete_tp',0),('partial_positive_hits',0),('complete_fp',1)]:
            candidate=copy.deepcopy(baseline);candidate['by_class']['billboard'][metric]=value
            self.assertFalse(gate(baseline,candidate)['passed'])
    def test_validation_selection_ignores_regression_and_retains_ties(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            root=Path(temp)
            for i in range(4):
                out=root/f'task-{i}/verified-123_{i}/output/rf-selector-123_{i}';out.mkdir(parents=True)
                (out/'best.pt').write_bytes(b'inert checkpoint fixture')
                (out/'transfer.json').write_text(json.dumps(dict(training_exit_code=0,postprocessing_exit_code=0)))
                (out/'experiment-report.json').write_text(json.dumps(dict(best_step=100,new_candidate_selected=True,best_checkpoint_sha256=sha(out/'best.pt'))))
                (out/'validation-0100.json').write_text(json.dumps(dict(metrics=dict(complete_tp=1,partial_hits=2,complete_f1=.5))))
                (out/'known-regression.json').write_text(json.dumps(dict(retention_passed=i!=0)))
            compare(root);result=read(root/'batch-comparison.json')
            self.assertEqual(result['validation_only_winner_index'],0)
            self.assertFalse(result['production_adoption'])
    def test_all_seals_and_local_pinned_runtime(self):
        receipt=verify(preparation_only=True);self.assertEqual(receipt['trial_tasks'],4)
        result=preflight(Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail'),local_cpu=True,preparation_only=True)
        self.assertEqual(result['starting_checkpoint_sha256'],'c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3')
        images=read(T/'known-regression/images.json');self.assertEqual(len(images),202)
        for h,row in images.items():self.assertEqual(sha(T/row['path']),h)
    def check_synthetic_result_archive(self,count,best,index=0):
        job='123_'+str(index);v=variant(T,index);schedule=self.fixtures[index][1]
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            root=Path(temp);archive=root/'synthetic.tar.gz';prefix='output/rf-selector-'+job+'/'
            pre=dict(active_classifier_heads=['class_embed','transformer.enc_out_class_embed.0'],region_overlay_sha256=sha(T/'region-review.json'),actual_job_id=job,protocol_sha256=identity['protocol_sha256'],active_classifier_rows=[133],test_photos_used=0,fresh_video_frames_used=0,starting_checkpoint_sha256='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',variant=v)
            report=dict(active_classifier_heads=['class_embed','transformer.enc_out_class_embed.0'],actual_job_id=job,approved_for_application=False,test_and_video_used=False,active_classifier_rows=[133],frozen_parameters_and_buffers_unchanged=True,inactive_classifier_rows_unchanged=True,retention_against_both_baselines=True,updates=count,best_step=best,new_candidate_selected=best>0,completion_reason='maximum-updates' if best else 'protocol-early-stop-no-gain',elapsed_seconds=1,variant=v,array_task_index=index,best_checkpoint_sha256=__import__('hashlib').sha256(b'inert').hexdigest(),last_checkpoint_sha256=__import__('hashlib').sha256(b'inert').hexdigest())
            with tarfile.open(archive,'w:gz') as tar:
                def add(name,data):
                    raw=data if isinstance(data,bytes) else json.dumps(data).encode();info=tarfile.TarInfo(prefix+name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
                add('preflight.json',pre);add('experiment-report.json',report);add('transfer.json',dict(actual_job_id=job,approved_for_application=False,process_exit_code=0,training_exit_code=0,finalized=True));add('best.pt',b'inert');add('last.pt',b'inert');add('sampling-plan.json',schedule)
                for step in range(1,count+1):add(f'step-{step:04}.json',dict(step=step,train_ids=schedule[step-1]))
                for step in range(0,count+1,100):add(f'validation-{step:04}.json',dict(step=step))
            result=verifier.verify(archive,job,sha(archive));self.assertEqual(result['updates'],count);self.assertEqual(result['best_step'],best)
            self.assertFalse(result['approved_for_application'])
    def test_result_verifier_accepts_full_no_gain_completion(self):self.check_synthetic_result_archive(1500,0)
    def test_result_verifier_accepts_full_maximum_completion_task3(self):self.check_synthetic_result_archive(3000,100,3)
if __name__=='__main__':unittest.main(verbosity=2)
