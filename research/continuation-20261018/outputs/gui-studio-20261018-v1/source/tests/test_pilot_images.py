"""No live network: bounded download, resume, JPEG, provenance and intake tests."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pilot_images', ROOT / 'scripts/acquire-pilot-images.py')
photo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photo)
ID = '0123456789abcdef'
URL = f'https://open-images-dataset.s3.amazonaws.com/train/{ID}.jpg'


class Response(io.BytesIO):
    def __init__(self, payload, url=URL, status=200, **headers):
        super().__init__(payload)
        self.status, self.url = status, url
        self.headers = {'Content-Length': str(len(payload)), 'ETag': '"same-object"', **headers}

    def geturl(self):
        return self.url


def checked(path):
    if Path(path).read_bytes() != b'abcdef':
        raise ValueError('not the expected test payload')
    return {'width': 10, 'height': 20, 'dhash': '0000000000000000', 'mean_luma': 50.0}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for name in ('images', 'receipts'):
            (self.directory / name).mkdir()
        self.context = {'selection_sha256': 'test'}

    def fetch(self, response, remaining=100):
        return photo.acquire_one(self.directory, ID, remaining, self.context,
                                 opener=lambda request, timeout: response, checker=checked)

    def test_complete_reused_without_network_and_mutation_rejected(self):
        receipt = self.fetch(Response(b'abcdef'))
        self.assertEqual(receipt['bytes'], 6)
        def no_network(*args, **kwargs):
            self.fail('Verified completed image must not be downloaded again')
        again = photo.acquire_one(self.directory, ID, 0, self.context, no_network, checked)
        self.assertEqual(receipt, again)
        (self.directory / 'images' / (ID + '.jpg')).write_bytes(b'changed')
        with self.assertRaises(photo.IntegrityError):
            photo.acquire_one(self.directory, ID, 100, self.context, no_network, checked)

    def test_truncation_resumes_exact_range(self):
        with self.assertRaises(photo.RetryableError):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        def resume(request, timeout):
            self.assertEqual(request.get_header('Range'), 'bytes=2-')
            self.assertEqual(request.get_header('If-range'), '"same-object"')
            return Response(b'cdef', status=206, **{'Content-Range': 'bytes 2-5/6'})
        photo.acquire_one(self.directory, ID, 4, self.context, resume, checked)
        self.assertEqual((self.directory / 'images' / (ID + '.jpg')).read_bytes(), b'abcdef')

    def test_changed_validator_and_ignored_range_preserve_partial(self):
        with self.assertRaises(photo.RetryableError):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        for response in (Response(b'cdef', status=206, **{'Content-Range': 'bytes 2-5/6', 'ETag': '"changed"'}),
                         Response(b'abcdef')):
            with self.assertRaises(photo.PermanentError):
                self.fetch(response)
        self.assertEqual((self.directory / 'images' / (ID + '.jpg.part')).read_bytes(), b'ab')

    def test_partial_prefix_mutation_rejected(self):
        with self.assertRaises(photo.RetryableError):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        (self.directory / 'images' / (ID + '.jpg.part')).write_bytes(b'xy')
        with self.assertRaises(photo.IntegrityError):
            self.fetch(Response(b'cdef', status=206, **{'Content-Range': 'bytes 2-5/6'}))

    def test_uncommitted_tail_recovered_from_verified_checkpoint(self):
        with self.assertRaises(photo.RetryableError):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        (self.directory / 'images' / (ID + '.jpg.part')).write_bytes(b'abXX')
        self.fetch(Response(b'cdef', status=206, **{'Content-Range': 'bytes 2-5/6'}))
        self.assertEqual((self.directory / 'images' / (ID + '.jpg')).read_bytes(), b'abcdef')

    def test_remaining_per_image_and_advertised_body_limits(self):
        for response, remaining in ((Response(b'abcdef'), 5),
                                    (Response(b'', **{'Content-Length': str(photo.IMAGE_CAP + 1)}), 1000000000),
                                    (Response(b'abcdef', **{'Content-Length': '5'}), 100)):
            with self.subTest(remaining=remaining), self.assertRaises(photo.PermanentError):
                self.fetch(response, remaining)
        self.assertFalse((self.directory / 'images' / (ID + '.jpg')).exists())

    def test_decode_failure_retained_and_full_partial_rechecked_without_network(self):
        with self.assertRaises(photo.PermanentError):
            self.fetch(Response(b'badpix'))
        def no_network(*args, **kwargs):
            self.fail('Full partial must be checked locally, not fetched again')
        with self.assertRaises(photo.PermanentError):
            photo.acquire_one(self.directory, ID, 0, self.context, no_network, checked)
        self.assertEqual((self.directory / 'images' / (ID + '.jpg.part')).read_bytes(), b'badpix')

    def test_receipt_before_publication_recovery(self):
        part = self.directory / 'images' / (ID + '.jpg.part')
        part.write_bytes(b'abcdef')
        photo.save(self.directory / 'receipts' / (ID + '.json'),
                   {'url': URL, 'context': self.context, 'status': 'downloaded', 'bytes': 6,
                    'sha256': photo.sha(part), 'decoded': checked(part)})
        def no_network(*args, **kwargs):
            self.fail('Recover publication without another transfer')
        photo.acquire_one(self.directory, ID, 0, self.context, no_network, checked)
        self.assertTrue((self.directory / 'images' / (ID + '.jpg')).exists())
        self.assertFalse(part.exists())

    def test_bad_ids_or_context_and_redirect_rejected(self):
        with self.assertRaises(photo.IntegrityError):
            photo.paths(self.directory, '../../unsafe')
        with self.assertRaises(photo.PermanentError):
            self.fetch(Response(b'abcdef', url='https://example.org/redirect'))
        self.fetch(Response(b'abcdef'))
        with self.assertRaises(photo.IntegrityError):
            photo.acquire_one(self.directory, ID, 100, {'selection_sha256': 'changed'}, checker=checked)

    def test_os_lock_prevents_concurrent_acquisition_and_releases(self):
        with photo.intake_lock(self.directory):
            with self.assertRaises(photo.IntegrityError):
                with photo.intake_lock(self.directory):
                    self.fail('Second lock should not be acquired')
        with photo.intake_lock(self.directory):
            pass


class JpegTests(unittest.TestCase):
    def test_real_jpeg_transfer_receipt_and_reuse(self):
        from PIL import Image
        payload = io.BytesIO()
        Image.new('RGB', (20, 10), (10, 20, 30)).save(payload, 'JPEG')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'images').mkdir()
            (directory / 'receipts').mkdir()
            record = photo.acquire_one(directory, ID, 10000000, {'test': 1},
                                       lambda request, timeout: Response(payload.getvalue()))
            self.assertEqual(record['decoded']['width'], 20)
            self.assertEqual(record['decoded']['height'], 10)
            self.assertEqual(record['sha256'], photo.sha(directory / 'images' / (ID + '.jpg')))
            self.assertEqual((directory / 'images' / (ID + '.jpg')).read_bytes(), payload.getvalue())
            def no_network(*args, **kwargs):
                self.fail('Reuse valid real JPEG without another request')
            self.assertEqual(photo.acquire_one(directory, ID, 0, {'test': 1}, no_network), record)

    def test_real_jpeg_decode_and_png_or_orientation_rejection(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'test.jpg'
            image = Image.new('RGB', (20, 10), (10, 20, 30))
            image.save(p, 'JPEG')
            info = photo.inspect_jpeg(p)
            self.assertEqual((info['width'], info['height']), (20, 10))
            image.save(p, 'PNG')
            with self.assertRaises(photo.PermanentError):
                photo.inspect_jpeg(p)
            exif = Image.Exif()
            exif[274] = 6
            image.save(p, 'JPEG', exif=exif)
            with self.assertRaises(photo.PermanentError):
                photo.inspect_jpeg(p)


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        base = self.root / 'output/training-general-v1'
        selection_dir = base / 'pilot-selection-v2-7449188'
        source_dir = base / 'catalogue-7447265'
        scope = base / 'metadata-tools-v1/general-intake-pilot.json'
        exclusion = self.root / 'output/training-0.13/general-smoke-bundle/manifest.json'
        registry = self.root / 'dependencies/recognition-vocabulary.json'
        source_dir.mkdir(parents=True)
        scope.parent.mkdir()
        exclusion.parent.mkdir(parents=True)
        registry.parent.mkdir()
        shutil.copytree(ROOT / 'output/kit-results/7449188/pilot-selection-v2-7449188', selection_dir)
        shutil.copyfile(ROOT / 'training/general-intake-pilot.json', scope)
        shutil.copyfile(ROOT / 'output/training-0.13/general-smoke-bundle/manifest.json', exclusion)
        shutil.copyfile(ROOT / 'dependencies/recognition-vocabulary.json', registry)
        v = photo.read(registry)
        classes = [(i, name, v['openimages_ids'][i]) for i, name in enumerate(v['openimages_labels'])]
        by_name = {v['classes'][canonical]: raw for raw, _, canonical in classes}
        selection = photo.read(selection_dir / 'selection.json')
        db_path = source_dir / 'openimages-train.sqlite'
        with contextlib.closing(sqlite3.connect(db_path)) as db:
            db.executescript('''CREATE TABLE meta(key TEXT, value TEXT);
              CREATE TABLE classes(raw_id INTEGER, name TEXT, canonical_id INTEGER);
              CREATE TABLE images(id TEXT, landing_url TEXT, original_url TEXT, license TEXT,
                                  author TEXT, author_url TEXT, title TEXT, rotation TEXT);
              CREATE TABLE boxes(image_id TEXT, raw_id INTEGER, x1 REAL, y1 REAL, x2 REAL, y2 REAL,
                                 occluded INTEGER, truncated INTEGER, group_of INTEGER, depiction INTEGER, source TEXT);''')
            db.execute('INSERT INTO meta VALUES(?,?)', ('source', json.dumps(selection['source'])))
            db.executemany('INSERT INTO classes VALUES(?,?,?)', classes)
            for item in selection['images'][:60]:
                db.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?)', (item['id'], 'https://example.org/public-photo',
                           'https://example.org/public.jpg', 'https://creativecommons.org/licenses/by/2.0/',
                           '<script>unsafe author text</script>', 'https://example.org/author', 'title', '0'))
                db.execute('INSERT INTO boxes VALUES(?,?,?,?,?,?,?,?,?,?,?)', (item['id'], by_name[item['selected_category']],
                           .1, .2, .8, .9, 0, 0, 0, 0, 'fixture'))
            db.commit()
        self.db_hash = photo.sha(db_path)
        report = photo.read(selection_dir / 'selection-summary.json')
        report['source_catalogue_sha256'] = self.db_hash
        photo.save(selection_dir / 'selection-summary.json', report)
        photo.save(source_dir / 'preparation.json', {'status': 'completed', 'publisher_split': 'train',
                   'catalogue_sha256': self.db_hash, 'scope_sha256': report['scope_sha256']})
        self.args = argparse.Namespace(root=self.root, selection_job='7449188', job_id='100', run=False)
        self.directory = base / 'photo-pilot-7449188-first60'
        self.calls = []

    def opener(self, request, timeout):
        self.calls.append(request.full_url)
        return Response(b'abcdef', url=request.full_url)

    def invoke(self, opener=None):
        with patch.object(photo, 'CATALOGUE_SHA', self.db_hash), contextlib.redirect_stdout(io.StringIO()):
            photo.run(self.args, opener or self.opener, checked, lambda seconds: None)

    def test_preflight_then_full_intake_and_restart_no_network(self):
        self.invoke()
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.calls, [])
        self.args.run = True
        self.invoke()
        self.assertEqual(len(self.calls), 60)
        report = photo.read(self.root / 'output/training-general-v1/photo-job-100/acquisition.json')
        manifest = photo.read(self.directory / 'manifest.json')
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['photographs_downloaded'], 60)
        self.assertEqual(report['downloaded_anchor_categories'], 52)
        self.assertEqual(report['original_bytes'], 360)
        self.assertTrue(all(item['split'] == 'unassigned' and not item['review']['complete_target_classes']
                            and not item['review']['rights_verified'] for item in manifest['images']))
        self.assertIn('&lt;script&gt;unsafe author', (self.directory / 'review.html').read_text(encoding='utf-8'))
        self.assertNotIn('<script>unsafe author', (self.directory / 'review.html').read_text(encoding='utf-8'))
        self.assertEqual((self.directory / 'review-notes-template.md').read_text(encoding='utf-8').count('## '), 60)
        (self.directory / 'review-notes-template.md').write_text('MY NOTES', encoding='utf-8')
        self.args.job_id = '101'
        def no_network(*args, **kwargs):
            self.fail('Completed pilot must reuse all photos')
        self.invoke(no_network)
        self.assertEqual((self.directory / 'review-notes-template.md').read_text(), 'MY NOTES')
        self.assertEqual(photo.read(self.directory / 'progress.json')['job_id'], '101')

    def test_404_is_visible_no_replacement_and_failed_job(self):
        self.args.run = True
        def unavailable(request, timeout):
            if not self.calls:
                self.calls.append(request.full_url)
                raise urllib.error.HTTPError(request.full_url, 404, 'not found', {}, None)
            return self.opener(request, timeout)
        with self.assertRaises(RuntimeError):
            self.invoke(unavailable)
        report = photo.read(self.directory / 'progress.json')
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['photographs_downloaded'], 59)
        self.assertEqual(len(report['failed_images']), 1)
        self.assertEqual(report['failed_images'][0]['attempts_this_job'], 1)
        self.assertEqual(len(self.calls), 60)

    def test_reviewed_manifest_edits_and_completed_corruption_are_preserved(self):
        self.args.run = True
        self.invoke()
        manifest_path = self.directory / 'manifest.json'
        edited = photo.read(manifest_path)
        edited['images'][0]['review']['reviewer'] = 'manual note'
        photo.save(manifest_path, edited)
        self.args.job_id = '101'
        with self.assertRaises(photo.IntegrityError):
            self.invoke()
        self.assertEqual(photo.read(manifest_path)['images'][0]['review']['reviewer'], 'manual note')

    def test_frozen_selection_mutation_rejected_before_network(self):
        path = self.root / 'output/training-general-v1/pilot-selection-v2-7449188/selection.json'
        path.write_text('{}', encoding='utf-8')
        self.args.run = True
        with self.assertRaises(photo.IntegrityError):
            self.invoke()
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
