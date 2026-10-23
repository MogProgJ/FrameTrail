import hashlib,io,json,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
class Contracts(unittest.TestCase):
    def invoke(self,member=None,bad_sha=False):
        with tempfile.TemporaryDirectory(dir=P) as folder:
            root=Path(folder);archive=root/'fixture.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                if member is not None:tar.addfile(member)
                else:
                    raw=json.dumps(dict(actual_job_id='123',process_exit_code=73,report_finalized=False,training=False,approved_for_training=False)).encode();info=tarfile.TarInfo('output/billboard-data-refresh-123/transfer.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            digest='0'*64 if bad_sha else hashlib.sha256(archive.read_bytes()).hexdigest()
            result=subprocess.run([sys.executable,'-B','-X','utf8',str(P/'verify_results.py'),'--archive',str(archive),'--job','123','--expected-sha',digest],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            return result.returncode,result.stdout,result.stderr
    def test_failed_task_is_preserved_without_training_clearance(self):
        code,out,_=self.invoke();self.assertEqual(code,0);self.assertEqual(json.loads(out)['status'],'failed-or-partial-data-job-preserved');self.assertFalse(json.loads(out)['approved_for_training'])
    def test_checksum_mismatch_fails(self):self.assertNotEqual(self.invoke(bad_sha=True)[0],0)
    def test_traversal_and_wrong_job_namespace_fail(self):
        for name in ('../../escape','output/billboard-data-refresh-124/transfer.json'):
            self.assertNotEqual(self.invoke(tarfile.TarInfo(name))[0],0)
    def test_archive_link_fails(self):
        link=tarfile.TarInfo('output/billboard-data-refresh-123/link');link.type=tarfile.SYMTYPE;link.linkname='../../escape';self.assertNotEqual(self.invoke(link)[0],0)
if __name__=='__main__':unittest.main(verbosity=2)
