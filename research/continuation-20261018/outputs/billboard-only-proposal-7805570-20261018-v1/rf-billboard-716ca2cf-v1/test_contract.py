"""CPU preparation contracts; synthetic update only, never real model training."""
import unittest
from pathlib import Path
import torch
from continuation_guard import inputs,approval,stop_without_gain
from head_policy import configure
from selection_policy import eligible
T=Path(__file__).resolve().parent
class ProposalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=inputs(T,require_approval=False)
    def test_schedule_has_3000_training_only_four_photo_batches(self):
        release,schedule,_,_=self.fixture;train={r['image_id'] for r in release['images'] if r['split']=='train'}
        self.assertEqual(len(schedule),3000);self.assertTrue(all(len(b)==len(set(b))==4 and set(b)<=train for b in schedule))
    def test_new_job_approval_is_absent_and_required(self):
        self.assertFalse((T/'approval.json').exists())
        with self.assertRaisesRegex(ValueError,'Explicit user approval'):approval(T)
    def test_stop_at_1500_only_without_gain(self):
        self.assertTrue(stop_without_gain(1500,0));self.assertFalse(stop_without_gain(1000,0));self.assertFalse(stop_without_gain(1500,100))
    def test_current_baseline_retains_original(self):
        _,_,original,resume=self.fixture;self.assertTrue(eligible(resume,original))
    def test_synthetic_optimizer_changes_only_billboard_row(self):
        net=torch.nn.Module();net.class_embed=torch.nn.Linear(4,616);net.backbone=torch.nn.Linear(4,4)
        optimizer,check=configure(net,[133],.0001);before={k:v.clone() for k,v in net.state_dict().items()}
        net.class_embed(torch.ones(2,4)).square().sum().backward();optimizer.step();check()
        inactive=[i for i in range(616) if i!=133]
        for k in ['class_embed.weight','class_embed.bias']:self.assertTrue(torch.equal(before[k][inactive],net.state_dict()[k][inactive]))
        self.assertFalse(torch.equal(before['class_embed.weight'][133],net.class_embed.weight[133]))
        for k in ['backbone.weight','backbone.bias']:self.assertTrue(torch.equal(before[k],net.state_dict()[k]))
if __name__=='__main__':unittest.main()
