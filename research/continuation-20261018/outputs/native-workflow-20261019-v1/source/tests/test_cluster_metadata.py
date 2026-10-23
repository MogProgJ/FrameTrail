import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cluster_metadata', ROOT / 'scripts/acquire-cluster-metadata.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)
URL = 'https://storage.googleapis.com/openimages/test/metadata.csv'


class Response(io.BytesIO):
    def __init__(self, payload, status=200, **headers):
        super().__init__(payload)
        self.status = status
        self.headers = {'Content-Length': str(len(payload)), 'ETag': '"version-1"', **headers}

    def geturl(self):
        return URL


class MetadataAcquisition(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.entry = {'filename': 'metadata.csv', 'url': URL, 'http_content_length_observed': 6}

    def tearDown(self):
        self.temporary.cleanup()

    def fetch(self, response):
        return metadata.acquire(self.entry, self.directory, opener=lambda request, timeout: response)

    def test_complete_download_records_hash_and_reuses_without_network(self):
        record = self.fetch(Response(b'abcdef'))
        self.assertEqual(record['sha256'], metadata.sha256(self.directory / 'metadata.csv'))
        self.assertFalse((self.directory / 'metadata.csv.part').exists())
        def no_network(request, timeout):
            self.fail('Completed files must be verified and reused without a new request')
        self.assertEqual(metadata.acquire(self.entry, self.directory, no_network), record)

    def test_truncation_resumes_with_validator_and_exact_content_range(self):
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        self.assertFalse((self.directory / 'metadata.csv').exists())
        def resume(request, timeout):
            self.assertEqual(request.get_header('Range'), 'bytes=2-')
            self.assertEqual(request.get_header('If-range'), '"version-1"')
            return Response(b'cdef', status=206, **{'Content-Range': 'bytes 2-5/6'})
        metadata.acquire(self.entry, self.directory, resume)
        self.assertEqual((self.directory / 'metadata.csv').read_bytes(), b'abcdef')

    def test_changed_object_or_ignored_range_preserves_partial(self):
        with self.assertRaises(ValueError):
            self.fetch(Response(b'ab', **{'Content-Length': '6'}))
        with self.assertRaisesRegex(ValueError, 'same metadata'):
            self.fetch(Response(b'cdef', status=206,
                                **{'Content-Range': 'bytes 2-5/6', 'ETag': '"version-2"'}))
        with self.assertRaisesRegex(ValueError, 'same metadata'):
            self.fetch(Response(b'abcdef'))
        self.assertEqual((self.directory / 'metadata.csv.part').read_bytes(), b'ab')

    def test_body_cannot_exceed_expected_budget(self):
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            self.fetch(Response(b'abcdefg', **{'Content-Length': '6'}))
        self.assertFalse((self.directory / 'metadata.csv').exists())

    def test_completed_file_mutation_and_changed_length_are_rejected(self):
        self.fetch(Response(b'abcdef'))
        (self.directory / 'metadata.csv').write_bytes(b'ABCDEF')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.fetch(Response(b'abcdef'))

    def test_source_limits_and_path_traversal_are_rejected(self):
        source = {'schema': 1, 'publisher_split': 'train', 'files': [self.entry],
                  'suggested_metadata_download_cap_bytes': 6}
        self.assertEqual(metadata.validate_sources(source), 6)
        source['suggested_metadata_download_cap_bytes'] = 5
        with self.assertRaisesRegex(ValueError, 'budget'):
            metadata.validate_sources(source)
        source['suggested_metadata_download_cap_bytes'] = 6
        self.entry['filename'] = '../metadata.csv'
        with self.assertRaisesRegex(ValueError, 'filename'):
            metadata.validate_sources(source)


if __name__ == '__main__':
    unittest.main()
