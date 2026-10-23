"""Synthetic SQLite selection and safety contracts; no network or real jobs."""
import copy,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import collector as c
class Contracts(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE images(id TEXT,landing_url TEXT,original_url TEXT,license TEXT,author TEXT,author_url TEXT,title TEXT,rotation TEXT)')
        self.db.execute('CREATE TABLE boxes(image_id TEXT,raw_id INT,x1 REAL,y1 REAL,x2 REAL,y2 REAL,occluded INT,truncated INT,group_of INT,depiction INT,source TEXT)')
        for i in range(160):
            self.db.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?)',(f'{i:016x}',f'https://www.flickr.com/photos/u{i}/{i+1}','unused','https://creativecommons.org/licenses/by/2.0/',f'u{i}',f'https://www.flickr.com/people/u{i}/','synthetic','0'))
            self.db.execute('INSERT INTO boxes VALUES(?,?,?,?,?,?,?,?,?,?,?)',(f'{i:016x}',46 if i%2 else 575,.1,.1,.8,.8,0,0,0,0,'xclick'))
        self.plan=dict(selection_seed='fixture',maximum_photos=8,anchors=[dict(name='billboard',raw_id=46,quota=dict(train=2,val=1,test=1)),dict(name='washing machine',raw_id=575,quota=dict(train=2,val=1,test=1))])
        self.classes=[dict(raw_id=46,canonical_name='billboard',canonical_id=133),dict(raw_id=575,canonical_name='washing machine',canonical_id=593)]
        self.excluded=dict(images=[dict(id='0000000000000000',group_id='https://www.flickr.com/people/u1/')])
    def tearDown(self):self.db.close()
    def select(self):return c.select_rows(self.db,self.plan,self.excluded,self.classes)[0]
    def test_deterministic_disjoint_bounded_selection(self):
        a=self.select();self.assertEqual(a,self.select());self.assertEqual(len(a),8);self.assertEqual(len({r['author_alias'] for r in a}),8)
        self.assertFalse({'0000000000000000','0000000000000001'}&{r['id'] for r in a})
        self.assertTrue(all(r['prospective_split']==c.split_for(r['author_alias'],'fixture') for r in a))
    def test_missing_anchors_preserve_shortfall_no_other_category(self):
        self.db.execute('DELETE FROM boxes WHERE raw_id=46');a,short=c.select_rows(self.db,self.plan,self.excluded,self.classes)
        self.assertEqual(len(a),4);self.assertEqual(short[0]['selected'],dict(train=0,val=0,test=0))
    def test_wrong_license_rotation_source_and_depiction_excluded(self):
        for statement in ["UPDATE images SET license='not-eligible'","UPDATE images SET rotation='90'","UPDATE images SET landing_url='https://example.invalid/'","UPDATE boxes SET depiction=1"]:
            self.db.execute('SAVEPOINT t');self.db.execute(statement);self.assertEqual(self.select(),[]);self.db.execute('ROLLBACK TO t');self.db.execute('RELEASE t')
    def test_author_aliases_unify_people_and_photos(self):
        self.assertEqual(c.group('https://www.flickr.com/photos/TEST/123'),c.group('https://www.flickr.com/people/test/'))
    def test_sources_stay_held_and_total_page_cap(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder);(path/'pages').mkdir();(path/'source-receipts').mkdir();item=self.select()[0]
            result=c.page_record(path,item,4,fetcher=lambda url:(b'too large',{}));self.assertEqual(result['status'],'held-source-unavailable');self.assertFalse(result['rights_verified'])
    def test_source_success_is_not_rights_or_training_approval(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder);(path/'pages').mkdir();(path/'source-receipts').mkdir();result=c.page_record(path,self.select()[0],100,fetcher=lambda url:(b'<html>fixture</html>',{}))
            self.assertEqual(result['status'],'retrieved-unreviewed');self.assertFalse(result['approved_for_training'])
    def test_image_redirect_has_no_fallback(self):
        with self.assertRaises(c.transport.PermanentError):c.NoImageRedirect().redirect_request(None,None,None,None,None,None)
    def test_partial_image_bytes_count_against_total_budget(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder);(path/'images').mkdir();(path/'images/a.jpg.part').write_bytes(b'12345');(path/'images/b.jpg').write_bytes(b'123')
            self.assertEqual(c.remaining_image_budget(path,dict(maximum_original_bytes=10)),2)
    def test_manifest_keeps_source_annotations_unknown_and_duplicates_held(self):
        item=self.select()[0];record=dict(bytes=1,sha256='a'*64,decoded=dict(width=100,height=100,dhash='0'*16,mean_luma=100))
        value=c.transport.make_manifest(dict(images=[item],selection_job='123',context={}),{item['id']:record},{item['id']:dict(attribution=item['attribution'],boxes=item['publisher_boxes'])},self.classes,{},[dict(id='prior',sha256='a'*64,dhash='0'*16)])
        self.assertFalse(value['approved_for_training']);self.assertEqual(value['images'][0]['split'],'unassigned');self.assertIn('exact-duplicate-review',value['images'][0]['intake_hold_reasons']);self.assertFalse(value['images'][0]['review']['complete_target_classes'])
if __name__=='__main__':unittest.main(verbosity=2)
