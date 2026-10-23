"""Adversarial scope/selection/archive/patch tests plus real model roundtrip. No optimizer updates."""
import unittest,tempfile,tarfile,io,copy,sys,json,math,hashlib
from contextlib import contextmanager
import uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'tools')]
from batch_guard import *
from admission import account
@contextmanager
def fixture_directory():
    # Retain fixtures inside this verified writable task folder; no system-temp writes/deletes.
    root=HERE/'test-fixtures'/str(uuid.uuid4());root.mkdir(parents=True)
    assert root.resolve().is_relative_to(HERE.resolve())
    yield str(root)

class Guards(unittest.TestCase):
    def test_archive_paths_links_duplicates_and_size(self):
        for name,kind,size in (('../escape','file',1),('/escape','file',1),('C:/escape','file',1),('x','link',0),('x','file',100)):
            with self.subTest(name=name,kind=kind,size=size),fixture_directory() as d:
                path=Path(d)/'x.tar.gz'
                with tarfile.open(path,'w:gz') as tf:
                    info=tarfile.TarInfo(name);info.size=size
                    if kind=='link':info.type=tarfile.SYMTYPE;info.linkname='../escape'
                    tf.addfile(info,io.BytesIO(b'x'*size) if kind=='file' else None)
                with self.assertRaises(ValueError):safe_extract(path,Path(d)/'out',max_bytes=10)
                self.assertFalse((Path(d)/'out').exists())
        with fixture_directory() as d:
            p=Path(d)/'duplicate.tar.gz'
            with tarfile.open(p,'w:gz') as tf:
                for _ in (0,1):
                    info=tarfile.TarInfo('same');info.size=1;tf.addfile(info,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):safe_extract(p,Path(d)/'out')
    def test_file_seal_tamper(self):
        with fixture_directory() as d:
            root=Path(d);(root/'x').write_bytes(b'a');write(root/'package-files.json',{'x':sha(root/'x')});verify_files(root)
            (root/'x').write_bytes(b'b')
            with self.assertRaises(ValueError):verify_files(root)
    def test_both_seed_method_and_ranking(self):
        def candidate(seed,step,hits=3,index=2):return dict(seed=seed,step=step,index=index,fresh=dict(complete_f1=.4,complete_tp=hits,complete_fp=0))
        a=dict(method='M1',seed=17,complete=True,best=candidate(17,250));b=dict(method='M1',seed=29,complete=True,best=None)
        self.assertIsNone(choose([a,b]));b['best']=candidate(29,100,index=3);self.assertEqual(choose([a,b])['step'],100)
        b['complete']=False;self.assertIsNone(choose([a,b]))
    def test_original_unknown_cap_and_gain_false_alarm(self):
        sys.path.insert(0,str(HERE.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'))
        def old(n):return dict(metrics=dict(unscored_predictions=n),per_class={'133':dict(complete_tp=0,complete_fp=0,partial_hits=0)})
        start=dict(complete_tp=0,complete_fp=0);f=dict(complete_tp=3,complete_fp=0)
        self.assertTrue(qualification(old(530),f,old(525),old(528),start)['qualifies'])
        self.assertFalse(qualification(old(531),f,old(525),old(528),start)['qualifies'])
        self.assertFalse(qualification(old(528),dict(complete_tp=3,complete_fp=1),old(525),old(528),start)['qualifies'])
        self.assertFalse(qualification(old(528),dict(complete_tp=2,complete_fp=0),old(525),old(528),start)['qualifies'])
    def test_quota_evidence_fail_closed(self):
        with fixture_directory() as d:
            root=Path(d)
            for name,value in {'user-default.txt':'ka_udxvl|ka_stud|\n','account-limits.txt':'ka_udxvl|ka_stud||normal|||gres/gpu=2|\n','qos-live.txt':'normal|2|4|gres/gpu=2|01:00:00|','partition-live.txt':'PartitionName=gpu_a100_il State=UP'}.items():(root/name).write_text(value)
            self.assertEqual(account(root,'ka_udxvl'),'ka_stud')
            (root/'account-limits.txt').write_text('')
            with self.assertRaises(ValueError):account(root,'ka_udxvl')
    def test_patch_shapes_scope_job_and_inactive_fingerprint(self):
        import torch
        state={k:torch.zeros((616,256) if k.endswith('weight') else (616,)) for k in KEYS};state['box.weight']=torch.ones(2)
        meta=dict(scope_sha256='scope',seed=17,step=100,starting_checkpoint_sha256=CHECKPOINT,actual_job_id='123_0')
        p=make_patch(state,meta);check_patch(p,'scope',17,100,'123_0');before=frozen_digest(state)
        state[KEYS[0]][133,0]=2;self.assertEqual(before,frozen_digest(state))
        state[KEYS[0]][134,0]=2;self.assertNotEqual(before,frozen_digest(state))
        for scope,seed,step,job in [('wrong',17,100,'123_0'),('scope',29,100,'123_0'),('scope',17,250,'123_0'),('scope',17,100,'124_0')]:
            with self.assertRaises(ValueError):check_patch(p,scope,seed,step,job)
        p['rows']['box.weight']=torch.zeros(2)
        with self.assertRaises(ValueError):check_patch(p,'scope',17,100)
    def test_frozen_schedule_validation_leak(self):
        c=HERE.parent/'fresh-paired-controls-20261021-v1';inputs=read(c/'INPUTS.json')['records'];schedule=read(c/'schedule-17.json')
        validate_inputs(inputs,[schedule]);mutated=copy.deepcopy(schedule);mutated[0][0]=next(r['image_id'] for r in inputs if r['pool']=='fresh_validation')
        with self.assertRaises(ValueError):validate_inputs(inputs,[mutated])
    def test_result_identity_partial_budget_and_checkpoint_set(self):
        import torch
        from verify_results import verify_result
        base=HERE/'rf-fresh-selector-v1';s=read(base/'SCOPE.json');scope_sha=sha(base/'SCOPE.json');job='123456';index=0;seed=17;run_id=job+'_0'
        with fixture_directory() as d:
            root=Path(d);patches=[];rows={k:torch.zeros((616,256) if k.endswith('weight') else (616,)) for k in KEYS}
            meta=dict(actual_job_id=run_id,scope_sha256=scope_sha,seed=17,index=0,starting_checkpoint_sha256=CHECKPOINT,schedule_sha256=s['schedule_sha256']['17'],frozen_digest='mock-fixture-only',production_adoption=False)
            for step in STEPS:
                name=f'patch-{step:04}.pt';torch.save(make_patch(rows,dict(meta,step=step)),root/name);patches.append(dict(step=step,path=name,sha256=sha(root/name)))
            torch.save(make_patch(rows,dict(meta,step=1500)),root/'last.pt')
            with (root/'TRAINING_STEPS.jsonl').open('w') as f:
                for n,batch in enumerate(read(base/'schedule-17.json'),1):f.write(json.dumps(dict(step=n,train_ids=batch,loss=1.,dense_loss=1.,gradient_norm=.1))+'\n')
            for name,value in {'user-default.txt':'ka_udxvl|ka_stud|\n','account-limits.txt':'ka_udxvl|ka_stud||normal|||gres/gpu=2|\n','qos-live.txt':'normal|2|4|gres/gpu=2|01:00:00|','partition-live.txt':'PartitionName=gpu_a100_il State=UP','admission-test.txt':'mock-success','submission-reply.txt':job+';uc3'}.items():(root/name).write_text(value)
            report=dict(status='complete-awaiting-local-CPU-selection',**meta,updates=1500,elapsed_active_seconds=600.,patches=patches,last_sha256=sha(root/'last.pt'),frozen_state_unchanged=True,inactive_rows_bitwise_unchanged=True,validation_selection_performed=False,test_photos_used=0,automatic_retries=0)
            exit_record=dict(actual_job_id=run_id,scope_sha256=scope_sha,process_exit_code=0)
            def reseal():
                (root/'REPORT.json').write_text(json.dumps(report));(root/'EXIT.json').write_text(json.dumps(exit_record))
                records={p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name!='result-files.json'}
                (root/'result-files.json').write_text(json.dumps(records))
            reseal();self.assertTrue(verify_result(root,base,job,index)['complete'])
            with self.assertRaises(ValueError):verify_result(root,base,'123457',index)
            for key,value in [('updates',1499),('test_photos_used',1),('elapsed_active_seconds',1800),('elapsed_active_seconds',float('nan'))]:
                before=report[key];report[key]=value;reseal()
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):verify_result(root,base,job,index)
                report[key]=before
            exit_record['process_exit_code']=124;reseal();self.assertFalse(verify_result(root,base,job,index)['complete'])

if __name__=='__main__':unittest.main(verbosity=2)
