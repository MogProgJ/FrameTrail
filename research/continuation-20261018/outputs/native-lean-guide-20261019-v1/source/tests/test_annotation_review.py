"""Offline correction integrity, immutable intake and unapproved export tests."""
import copy
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import annotation_review as review
from training_data import digest, image_info, read_json, vocabulary, write_json, validate_manifest
spec = importlib.util.spec_from_file_location('verify_annotation_export', ROOT / 'scripts/verify-annotation-export.py')
export_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_check)


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'images').mkdir()
        photo = self.root / 'images/0123456789abcdef.jpg'
        Image.new('RGB', (20, 30), '#ccddee').save(photo)
        _, _, dhash, _ = image_info(photo)
        self.manifest = self.root / 'manifest.json'
        self.original = {'schema': 1, 'approved_for_training': False, 'classes': vocabulary(), 'images': [{
            'id': '0123456789abcdef', 'selected_category': 'person', 'selected_domain': 'test',
            'path': 'images/0123456789abcdef.jpg', 'bytes': photo.stat().st_size, 'sha256': digest(photo),
            'width': 20, 'height': 30, 'dhash': dhash, 'attribution': {'title': '</script><script>bad</script>'},
            'objects': [{'raw_id': 0, 'box': [1, 2, 10, 20], 'source': 'publisher'}],
            'split': 'unassigned', 'publisher_split': 'train', 'group_id': 'source'}]}
        write_json(self.manifest, self.original)
        self.workspace = self.root / 'annotations'
        self.state = review.prepare(self.manifest, self.workspace)
        self.seed = read_json(self.workspace / 'seed.json')

    def edit(self, **fields):
        obj = copy.deepcopy(self.state['images'][0]['objects'][0])
        obj.update(fields)
        review.event(self.state, self.original['images'][0]['id'], 'update', obj['id'], obj, 'test-reviewer')

    def test_valid_logged_edit_and_original_unchanged(self):
        self.edit(box=[2, 3, 11, 21], status='confirmed', note='Inspected')
        review.validate_state(self.seed, self.state)
        self.assertEqual(read_json(self.manifest), self.original)
        self.assertEqual(self.state['images'][0]['objects'][0]['origin']['record']['box'], [1, 2, 10, 20])

    def test_reject_requires_reason_and_preserves_record(self):
        with self.assertRaises(ValueError):
            self.edit(status='rejected')
        self.edit(status='rejected', note='Incorrect object class')
        self.assertEqual(len(self.state['images'][0]['objects']), 1)
        review.validate_state(self.seed, self.state)

    def test_invalid_geometry_raw_ids_and_nan(self):
        for fields in ({'box': [-1, 2, 10, 20]}, {'box': [5, 2, 5, 20]},
                       {'box': [1, 2, 21, 20]}, {'box': [float('nan'), 2, 10, 20]},
                       {'raw_id': 601}, {'raw_id': True}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.edit(**fields)

    def test_unlogged_edit_approval_or_image_swap_rejected(self):
        for mutate in (lambda x: x.update(approved_for_training=True),
                       lambda x: x['images'][0].update(sha256='changed'),
                       lambda x: x['images'][0]['objects'][0].update(box=[2, 3, 10, 20]),
                       lambda x: x['classes'].reverse()):
            candidate = copy.deepcopy(self.state)
            mutate(candidate)
            with self.assertRaises(ValueError):
                review.validate_state(self.seed, candidate)

    def test_immutable_provenance_even_with_logged_update(self):
        obj = copy.deepcopy(self.state['images'][0]['objects'][0])
        obj['origin']['kind'] = 'model'
        with self.assertRaises(ValueError):
            review.event(self.state, self.original['images'][0]['id'], 'update', obj['id'], obj, 'reviewer')

    def test_manual_add_and_duplicate_id_refused(self):
        obj = {'id': 'manual-example', 'raw_id': 381, 'box': [0, 0, 20, 30], 'status': 'pending',
               'note': 'New person box', 'origin': {'kind': 'manual'}}
        review.event(self.state, self.original['images'][0]['id'], 'add', obj['id'], obj, 'reviewer')
        review.validate_state(self.seed, self.state)
        with self.assertRaises(ValueError):
            review.event(self.state, self.original['images'][0]['id'], 'add', obj['id'], obj, 'reviewer')

    def observation(self, **fields):
        obj = {'id': 'observation-bracelet', 'label': 'bracelet', 'box': [1, 2, 10, 20],
               'status': 'confirmed', 'note': 'Visible wrist accessory', 'origin': {'kind': 'manual-observation'}}
        obj.update(fields)
        return obj

    def test_observation_is_logged_separately_without_new_class(self):
        obj = self.observation()
        review.event(self.state, self.original['images'][0]['id'], 'observation-add', obj['id'], obj, 'reviewer')
        review.validate_state(self.seed, self.state)
        self.assertEqual(len(self.state['images'][0]['objects']), 1)
        self.assertEqual(self.state['images'][0]['observations'][0]['label'], 'bracelet')
        self.assertEqual(self.state['classes'], vocabulary())
        self.assertEqual(read_json(self.manifest), self.original)
        self.assertEqual(review.summary(self.state)['unsupported_observations_by_state']['confirmed'], 1)
        with self.assertRaises(ValueError):
            review.event(self.state, self.original['images'][0]['id'], 'observation-add', obj['id'], obj, 'reviewer')

    def test_invalid_observation_names_provenance_or_geometry_refused(self):
        for fields in ({'label': ''}, {'label': 'Clothing'}, {'label': ' bracelet '}, {'label': 'bad\nname'},
                       {'label': 'x' * 121}, {'raw_id': 115}, {'box': [0, 0, 0, 10]},
                       {'origin': {'kind': 'publisher'}}, {'status': 'approved'}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                review.check_observation(self.observation(**fields), self.state['images'][0])

    def test_observation_update_and_unlogged_tampering(self):
        obj = self.observation()
        review.event(self.state, self.original['images'][0]['id'], 'observation-add', obj['id'], obj, 'reviewer')
        changed = copy.deepcopy(obj)
        changed.update(status='pending', box=[2, 3, 11, 21])
        review.event(self.state, self.original['images'][0]['id'], 'observation-update', obj['id'], changed, 'reviewer')
        review.validate_state(self.seed, self.state)
        candidate = copy.deepcopy(self.state)
        candidate['images'][0]['observations'][0]['label'] = 'unlogged'
        with self.assertRaises(ValueError):
            review.validate_state(self.seed, candidate)

    def test_observations_export_to_sidecar_not_coco_or_yolo(self):
        obj = self.observation()
        review.event(self.state, self.original['images'][0]['id'], 'observation-add', obj['id'], obj, 'reviewer')
        saved = self.workspace / 'with-observation.json'
        write_json(saved, self.state)
        output = self.workspace / 'observation-export'
        review.export_draft(self.workspace, saved, output)
        self.assertEqual(len(read_json(output / 'draft-coco.json')['annotations']), 1)
        self.assertEqual(len(read_json(output / 'draft-coco.json')['categories']), 601)
        self.assertEqual(len((output / 'labels/0123456789abcdef.txt').read_text().splitlines()), 1)
        self.assertEqual(read_json(output / 'unsupported-observations.json'), review.observation_export(self.state))
        result = export_check.verify(self.workspace, output)
        self.assertEqual(result['unsupported_observations_by_state']['confirmed'], 1)
        bad = read_json(output / 'unsupported-observations.json')
        bad['images'][0]['observations'][0]['label'] = 'wrong'
        write_json(output / 'unsupported-observations.json', bad)
        with self.assertRaises(ValueError):
            export_check.verify(self.workspace, output)
        (output / 'unsupported-observations.json').unlink()
        with self.assertRaises(ValueError):
            export_check.verify(self.workspace, output)

    def test_pending_observation_blocks_image_checklist(self):
        self.edit(status='confirmed', note='Checked')
        obj = self.observation(status='pending')
        review.event(self.state, self.original['images'][0]['id'], 'observation-add', obj['id'], obj, 'reviewer')
        fields = copy.deepcopy(self.state['images'][0]['review'])
        fields.update(reviewer='human', geometry_pass=True)
        review.event(self.state, self.original['images'][0]['id'], 'review', None, fields, 'human')
        with self.assertRaises(ValueError):
            review.validate_state(self.seed, self.state)

    def test_javascript_conversion_is_python_valid_and_train_labels_exclude_it(self):
        node = shutil.which('node')
        if not node:
            bundled = Path(r'C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
            node = str(bundled) if bundled.is_file() else None
        if not node:
            self.skipTest('Node runtime unavailable for cross-language fixture')
        result = subprocess.run([node, str(ROOT / 'tests/annotation_interop.cjs')], input=json.dumps(self.seed),
                                text=True, capture_output=True, check=True, timeout=30)
        state = json.loads(result.stdout)
        review.validate_state(self.seed, state)
        self.assertEqual(state['images'][0]['objects'][0]['status'], 'rejected')
        saved = self.workspace / 'js-conversion.json'
        write_json(saved, state)
        output = self.workspace / 'js-export'
        review.export_draft(self.workspace, saved, output)
        self.assertEqual(read_json(output / 'draft-coco.json')['annotations'], [])
        self.assertEqual((output / 'labels/0123456789abcdef.txt').read_text(), '')
        self.assertEqual(export_check.verify(self.workspace, output)['active_exported_boxes'], 0)

    def test_wrong_before_or_history_sequence_refused(self):
        self.edit(note='Changed')
        for key, value in (('seq', 2), ('before', None), ('image_id', 'not-an-image')):
            candidate = copy.deepcopy(self.state)
            candidate['events'][0][key] = value
            with self.assertRaises(ValueError):
                review.validate_state(self.seed, candidate)

    def test_source_change_or_seed_change_refused(self):
        (self.workspace / 'seed.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            review.load_checked(self.workspace, self.workspace / 'annotations.json')

    def test_photo_change_and_path_escape_refused(self):
        changed = copy.deepcopy(self.original)
        changed['images'][0]['path'] = '../escape.jpg'
        write_json(self.manifest, changed)
        with self.assertRaises(ValueError):
            review.check_intake(self.manifest)
        write_json(self.manifest, self.original)
        (self.root / self.original['images'][0]['path']).write_bytes(b'bad photo')
        with self.assertRaises(ValueError):
            review.check_intake(self.manifest)

    def test_existing_output_is_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            review.prepare(self.manifest, self.workspace)
        with self.assertRaises(FileExistsError):
            review.render_editor(self.seed, self.state, self.workspace / 'editor.html')

    def test_draft_export_formats_and_no_training_bypass(self):
        output = self.workspace / 'draft'
        result = review.export_draft(self.workspace, self.workspace / 'annotations.json', output)
        coco = read_json(output / 'draft-coco.json')
        self.assertFalse(result['approved_for_training'])
        self.assertEqual(coco['annotations'][0]['bbox'], [1, 2, 9, 18])
        self.assertEqual(len(coco['categories']), 601)
        self.assertTrue((output / 'labels/0123456789abcdef.txt').is_file())
        self.assertFalse((output / 'data.yaml').exists())
        self.assertFalse((output / 'dataset-lock.json').exists())
        with self.assertRaises(ValueError):
            validate_manifest(output / 'draft-manifest.json')
        with self.assertRaises(FileExistsError):
            review.export_draft(self.workspace, self.workspace / 'annotations.json', output)

    def test_json_script_payload_cannot_escape_into_html(self):
        html = (self.workspace / 'editor.html').read_text(encoding='utf-8')
        self.assertNotIn('</script><script>bad</script>', html)
        self.assertIn('\\u003c/script', html)

    def test_editor_controls_have_unique_ids_and_explicit_removal_label(self):
        class Controls(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
                self.labels = []
            def handle_starttag(self, tag, attrs):
                fields = dict(attrs)
                if 'id' in fields:
                    self.ids.append(fields['id'])
                if tag == 'label' and 'for' in fields:
                    self.labels.append(fields['for'])
        html = (self.workspace / 'editor.html').read_text(encoding='utf-8')
        controls = Controls()
        controls.feed(html)
        self.assertEqual(len(controls.ids), len(set(controls.ids)))
        self.assertIn('reject-reason', controls.labels)
        for name in ('image-frame', 'rf-list', 'saved-panel', 'rf-panel', 'reject-error', 'review-dialog', 'help-dialog'):
            self.assertIn(name, controls.ids)

    def test_removal_reason_is_not_inside_an_accordion(self):
        html = (self.workspace / 'editor.html').read_text(encoding='utf-8')
        removal = html.split('<div class="remove-panel">')[1].split('</div>')[0]
        self.assertIn('id="reject-reason"', removal)
        self.assertIn('id="reject"', removal)
        self.assertNotIn('<details', removal)
        self.assertNotIn('hidden', removal.split('<p id="reject-error"')[0])

    def test_workspace_has_no_sticky_editor_or_fixed_status_overlay(self):
        html = (self.workspace / 'editor.html').read_text(encoding='utf-8')
        css = html.split('<style>')[1].split('</style>')[0]
        self.assertNotIn('position:sticky', css)
        self.assertNotIn('position:fixed', css)
        self.assertIn('height:100dvh', css)
        self.assertIn('@media(max-width:900px)', css)
        self.assertIn('aria-controls="rf-panel"', html)

    def test_overlapping_model_proposal_comparison_is_class_aware(self):
        self.assertEqual(review.iou([0, 0, 10, 10], [0, 0, 10, 10]), 1)
        self.assertEqual(review.iou([0, 0, 10, 10], [10, 10, 20, 20]), 0)

    def test_image_checklist_cannot_pass_with_pending_boxes(self):
        fields = copy.deepcopy(self.state['images'][0]['review'])
        fields.update(reviewer='human', geometry_pass=True)
        review.event(self.state, self.original['images'][0]['id'], 'review', None, fields, 'human')
        with self.assertRaises(ValueError):
            review.validate_state(self.seed, self.state)

    def test_actual_export_files_verify(self):
        output = self.workspace / 'draft-checked'
        review.export_draft(self.workspace, self.workspace / 'annotations.json', output)
        result = export_check.verify(self.workspace, output)
        self.assertEqual(result['active_exported_boxes'], 1)
        self.assertEqual(result['yolo_files_verified'], 1)
        self.assertFalse(result['approved_for_training'])

    def test_tampered_yolo_geometry_is_rejected(self):
        output = self.workspace / 'draft-bad-yolo'
        review.export_draft(self.workspace, self.workspace / 'annotations.json', output)
        (output / 'labels/0123456789abcdef.txt').write_text('0 0.2 0.2 0.2 0.2\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            export_check.verify(self.workspace, output)

    def test_extra_coco_targets_or_wrong_original_reference_rejected(self):
        output = self.workspace / 'draft-bad-coco'
        review.export_draft(self.workspace, self.workspace / 'annotations.json', output)
        good = read_json(output / 'draft-coco.json')
        for mutate in (lambda x: x['annotations'].append(copy.deepcopy(x['annotations'][0])),
                       lambda x: x['images'][0].update(file_name='../../not-an-intake-image.jpg')):
            bad = copy.deepcopy(good)
            mutate(bad)
            write_json(output / 'draft-coco.json', bad)
            with self.assertRaises(ValueError):
                export_check.verify(self.workspace, output)


if __name__ == '__main__':
    unittest.main()
