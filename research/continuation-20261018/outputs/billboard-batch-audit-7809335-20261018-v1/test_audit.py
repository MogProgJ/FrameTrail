"""Audit fixtures use existing predictions and tiny tensors, never model inference."""
import copy,unittest
import torch
from audit_batch import TOOLS,read,variant,replay_validation,tensor_check
class AuditContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[r for r in read(TOOLS/'release/candidate-manifest-v2.json')['images'] if r['split']=='val']
        cls.original=read(TOOLS/'inputs/validation-original.json');cls.resume=read(TOOLS/'inputs/validation-resume.json')
    def baseline(self):return dict(self.resume,step=0,eligible=True)
    def test_current_baseline_and_ties_replay(self):
        baseline=self.baseline();tie=dict(baseline,step=100)
        step,_,trace=replay_validation(self.rows,[baseline,tie],self.original,self.resume)
        self.assertEqual(step,0);self.assertEqual(len(trace),2)
    def test_forged_metric_rejected(self):
        baseline=copy.deepcopy(self.baseline());baseline['metrics']['complete_tp']+=1
        with self.assertRaisesRegex(ValueError,'independent rescore'):replay_validation(self.rows,[baseline],self.original,self.resume)
    def test_active_row_allowed_inactive_row_and_features_rejected(self):
        reference={'class_embed.weight':torch.zeros(616,2),'class_embed.bias':torch.zeros(616),'feature':torch.ones(2)}
        other={k:v.clone() for k,v in reference.items()};other['class_embed.weight'][133]=1
        self.assertEqual(tensor_check(reference,other,True),['class_embed.weight'])
        with self.assertRaises(ValueError):tensor_check(reference,other,False)
        other['class_embed.bias'][593]=1
        with self.assertRaisesRegex(ValueError,'Inactive'):tensor_check(reference,other,True)
        other={k:v.clone() for k,v in reference.items()};other['feature'][0]=2
        with self.assertRaisesRegex(ValueError,'Frozen'):tensor_check(reference,other,True)
if __name__=='__main__':unittest.main(verbosity=2)
