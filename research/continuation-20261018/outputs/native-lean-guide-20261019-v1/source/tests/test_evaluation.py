import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('evaluation', Path(__file__).parents[1]/'scripts/evaluate-detectors.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

def box(cls=0, confidence=.9, coords=(0,0,10,10)):
    return dict(class_id=cls, confidence=confidence, box=coords)

class Matching(unittest.TestCase):
    def test_duplicate_cannot_match_twice(self):
        result=evaluation.score([box()], [box(), box(confidence=.8)], complete=True)
        self.assertEqual((result['matched'],result['false_positives'],result['precision']), (1,1,.5))
    def test_partial_labels_do_not_report_precision(self):
        result=evaluation.score([box()], [box(),box(2)])
        self.assertIsNone(result['precision'])
        self.assertIsNone(result['false_positives'])
    def test_wrong_class_is_not_a_match(self):
        result=evaluation.score([box(29)], [box(32)])
        self.assertEqual(result['matched'],0)
        self.assertEqual(len(result['unmatched_targets'][0]['overlapping_other_labels']),1)
    def test_one_prediction_cannot_match_two_targets(self):
        self.assertEqual(evaluation.score([box(),box()],[box()])['matched'],1)
    def test_low_overlap_and_empty_frames(self):
        self.assertEqual(evaluation.score([box()],[box(coords=(8,8,18,18))])['matched'],0)
        self.assertIsNone(evaluation.score([],[],True)['target_recall'])
        self.assertEqual(evaluation.score([],[box()],True)['false_positives'],1)
    def test_iou(self):
        self.assertEqual(evaluation.iou((0,0,10,10),(0,0,10,10)),1)
        self.assertAlmostEqual(evaluation.iou((0,0,10,10),(5,0,15,10)),1/3)

if __name__=='__main__': unittest.main()
