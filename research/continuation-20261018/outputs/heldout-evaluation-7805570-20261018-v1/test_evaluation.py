import copy, unittest
from pathlib import Path
import evaluate as e

class EvaluationContracts(unittest.TestCase):
    def ref(self):
        return dict(source_sha256='reference',vocabulary_sha256='vocabulary',
            vocabulary=[dict(canonical_id=0,canonical_name='complete'),dict(canonical_id=1,canonical_name='partial'),dict(canonical_id=2,canonical_name='unknown')],
            baseline_identity=dict(confidence=.35),evaluation=dict(iou_threshold=.5),
            frames=[dict(id='one',sha256='image',sequence='group',width=100,height=100,
                complete_class_scopes=[dict(canonical_id=0,complete=True)],
                targets=[dict(id='a',canonical_id=0,label='complete',box=[0,0,20,20]),dict(id='b',canonical_id=1,label='partial',box=[30,30,50,50])])])
    def pred(self,cid,box):return dict(canonical_id=cid,confidence=.8,box=box)
    def test_complete_partial_and_unknown_have_distinct_denominators(self):
        _,r=e.score_predictions(self.ref(),{'image':[self.pred(0,[0,0,20,20]),self.pred(0,[60,60,80,80]),self.pred(1,[30,30,50,50]),self.pred(1,[60,60,80,80]),self.pred(2,[60,60,80,80])]}, {})
        m=r['aggregate'];self.assertEqual((m['complete_tp'],m['complete_fp'],m['partial_positive_hits'],m['unscored_predictions']),(1,1,1,2))
    def test_duplicate_cannot_match_same_target_twice(self):
        _,r=e.score_predictions(self.ref(),{'image':[self.pred(0,[0,0,20,20])]*2},{})
        self.assertEqual((r['aggregate']['complete_tp'],r['aggregate']['complete_fp']),(1,1))
    def test_retention_checks_each_class_even_if_total_gain(self):
        b={'by_class':{'a':dict(complete_tp=1,complete_fp=0,partial_positive_hits=0),'b':dict(complete_tp=0,complete_fp=0,partial_positive_hits=0)}}
        c=copy.deepcopy(b);c['by_class']['a']['complete_tp']=0;c['by_class']['b']['complete_tp']=3
        self.assertFalse(e.gate(b,c)['passed'])
    def test_new_false_positive_class_fails_retention(self):
        b={'by_class':{}};c={'by_class':{'new':dict(complete_tp=0,complete_fp=1,partial_positive_hits=0)}}
        self.assertFalse(e.gate(b,c)['passed'])
    def test_photo_adapter_preserves_partial_vs_absent(self):
        row=dict(image_id='one',identity_group='author',width=100,height=100,source_path='images/one.jpg',image_sha256='digest',scope={'0':'positive_only','1':'absent'},targets=[dict(canonical_id=0,normalized_cxcywh=[.5,.5,.2,.4])])
        before=copy.deepcopy(row);f=e.photo_frame(row,['a','b'],Path('base'))
        self.assertEqual(row,before);self.assertEqual([s['canonical_id'] for s in f['complete_class_scopes']],[1]);self.assertEqual(f['targets'][0]['box'],[40,30,60,70])
    def test_missing_frame_rejected(self):
        with self.assertRaises(KeyError):e.score_predictions(self.ref(),{}, {})

if __name__=='__main__':unittest.main()
