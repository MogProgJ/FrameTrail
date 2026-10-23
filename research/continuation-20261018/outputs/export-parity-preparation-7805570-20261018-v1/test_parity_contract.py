import copy,unittest
from parity_contract import compare
def detection(cid=593,confidence=.8,box=None):return dict(canonical_id=cid,confidence=confidence,box=box or [10,10,50,50])
class ParityContracts(unittest.TestCase):
    def test_empty(self):self.assertTrue(compare([],[],100,100)['passed'])
    def test_permutation(self):
        a=[detection(),detection(133,box=[60,60,90,90])];self.assertTrue(compare(a,a[::-1],100,100)['passed'])
    def test_missing_detection(self):self.assertFalse(compare([detection()],[],100,100)['passed'])
    def test_changed_class(self):self.assertFalse(compare([detection()],[detection(133)],100,100)['passed'])
    def test_changed_confidence(self):self.assertFalse(compare([detection()],[detection(confidence=.81)],100,100)['passed'])
    def test_changed_geometry(self):self.assertFalse(compare([detection()],[detection(box=[20,20,60,60])],100,100)['passed'])
if __name__=='__main__':unittest.main()
