import importlib.util
from pathlib import Path
import unittest
import tempfile
spec=importlib.util.spec_from_file_location('tracking_evaluation',Path(__file__).parents[1]/'scripts/evaluate-tracking.py')
evaluation=importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

def reference(identity='a', coords=(0,0,10,10), cls=0):return dict(object_id=identity,class_id=cls,box=coords)
def prediction(seq=1, track=1, cls=0, coords=(0,0,10,10)):return dict(sequence=seq,track_id=track,class_id=cls,box=coords,confidence=.9)
def manifest():return dict(schema=1,width=100,height=100,frames=[dict(sequence=1,complete=False,objects=[reference()])],
                          events=dict(complete=False,start_sequence=1,end_sequence=10,items=[]))
class Scoring(unittest.TestCase):
    def test_partial_is_not_precision(self):
        result=evaluation.score(manifest(),[prediction(),prediction(track=2,cls=2)],[])
        self.assertEqual(result['matched'],1)
        self.assertIsNone(result['false_positives'])
        self.assertIsNone(result['events']['false_positives'])
    def test_identity_change_and_missed_sample(self):
        m=manifest();m['frames'] += [dict(sequence=2,complete=False,objects=[reference()]),dict(sequence=3,complete=False,objects=[reference()])]
        result=evaluation.score(m,[prediction(),prediction(seq=3,track=2)],[])
        self.assertEqual((result['matched'],result['missed'],result['id_changes_between_labelled_matches']),(2,1,1))
    def test_wrong_class_is_missed(self):self.assertEqual(evaluation.score(manifest(),[prediction(cls=2)],[])['matched'],0)
    def test_duplicate_and_direction(self):
        m=manifest();m['events'].update(complete=True,items=[dict(event_id='cross',object_id='a',sequence=1,direction='negative_to_positive')])
        events=[dict(sequence=1,track_id=1,class_id=0,direction='negative_to_positive')]*2
        result=evaluation.score(m,[prediction()],events)['events']
        self.assertEqual((result['matched'],result['false_positives'],result['duplicate_hints']),(1,1,1))
        events[0]=dict(sequence=1,track_id=1,class_id=0,direction='positive_to_negative')
        self.assertEqual(evaluation.score(m,[prediction()],events)['events']['matched'],1)
    def test_wrong_identity_and_event_outside_review(self):
        m=manifest();m['events'].update(complete=True,items=[dict(event_id='cross',object_id='a',sequence=1,direction='negative_to_positive')])
        result=evaluation.score(m,[prediction()],[dict(sequence=1,track_id=2,class_id=0,direction='negative_to_positive'),dict(sequence=11,track_id=1,class_id=0,direction='negative_to_positive')])['events']
        self.assertEqual((result['matched'],result['missed'],result['false_positives']),(0,1,1))
    def test_reused_track_rejected(self):
        with self.assertRaises(ValueError):evaluation.score(manifest(),[prediction(),prediction()],[])
    def test_bad_manifest_and_missing_event_anchor(self):
        m=manifest();m['frames'][0]['sequence']=0
        with self.assertRaises(ValueError):evaluation.validate(m)
        m=manifest();m['events']['items']=[dict(event_id='x',object_id='a',sequence=10,direction='negative_to_positive')]
        with self.assertRaises(ValueError):evaluation.score(m,[prediction()],[])
    def test_empty_complete_negative(self):
        m=manifest();m['frames'][0].update(complete=True,objects=[]);m['events']['complete']=True
        result=evaluation.score(m,[prediction()],[dict(sequence=1,track_id=1,class_id=0,direction='negative_to_positive')])
        self.assertEqual(result['false_positives'],1)
        self.assertEqual(result['events']['false_positives'],1)
        self.assertIsNone(result['target_recall'])
    def test_event_before_review_is_not_credited(self):
        m=manifest();m['frames'][0]['sequence']=5;m['events'].update(start_sequence=5,items=[dict(event_id='x',object_id='a',sequence=5,direction='negative_to_positive')])
        result=evaluation.score(m,[prediction(seq=5)],[dict(sequence=4,track_id=1,class_id=0,direction='negative_to_positive')])['events']
        self.assertEqual((result['matched'],result['missed'],result['reviewed_predictions']),(0,1,0))
    def test_bad_csv_headers_and_nonfinite_boxes(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'rows.csv';path.write_text('other\n')
            with self.assertRaises(ValueError):evaluation.read_csv(path)
            path.write_text('sequence,track_id,class_id,confidence,left,top,right,bottom\n1,1,0,.9,nan,0,10,10\n')
            with self.assertRaises(ValueError):evaluation.read_csv(path)
if __name__=='__main__':unittest.main()
