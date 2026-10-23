"""RF-DETR probe contracts tested without Torch, a checkpoint, network or model inference."""
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import rfdetr_probe as probe
review_spec = importlib.util.spec_from_file_location('probe_review',ROOT/'scripts/review-rfdetr-probe.py')
review = importlib.util.module_from_spec(review_spec)
review_spec.loader.exec_module(review)


class Response(io.BytesIO):
    def __init__(self, body, length, etag='publisher-object', url=None):
        super().__init__(body)
        self.headers = {'Content-Length':str(length), 'ETag':etag}
        self.url = url or probe.ASSET_URL
    def geturl(self):
        return self.url


class RFProbeTests(unittest.TestCase):
    def raw(self):
        boxes = np.array([[[.5,.5,.2,.4]]], dtype=np.float32)
        logits = np.full((1,1,91), -20., dtype=np.float32)
        logits[0,0,18] = 3.
        return {'dets':boxes, 'labels':logits}

    def test_coco_contract_preserves_existing_categories_and_is_not_adopted(self):
        info = probe.contract()
        self.assertEqual(len(info['classes']), 80)
        self.assertEqual(info['classes'][16], {'raw_slot':18, 'canonical_id':16, 'name':'dog'})
        self.assertEqual(probe.COCO_MAP[90], 79)
        self.assertIsNone(info['outputs']['background_class_id'])
        self.assertFalse(info['approved_for_application'])
        self.assertFalse(info['trained_by_frametrail'])

    def test_named_sparse_outputs_decode_to_original_pixel_coordinates(self):
        result = probe.decode_outputs(self.raw(), 100, 200)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['class_id'], 16)
        np.testing.assert_allclose(result[0]['box'], [40,60,60,140], atol=.00001)
        self.assertGreater(result[0]['confidence'], .95)
        self.assertEqual(probe.decode_outputs(dict(reversed(list(self.raw().items()))),100,200), result)

    def test_toothbrush_is_not_dropped_as_false_background(self):
        raw = self.raw()
        raw['labels'][0,0,90] = 4.
        result = probe.decode_outputs(raw,100,200)
        self.assertEqual(result[0]['class_id'],79)
        self.assertEqual(len(result),2)  # Multiple classes per query; no YOLO NMS here.

    def test_unused_sparse_slots_are_never_application_classes(self):
        raw = self.raw()
        raw['labels'][0,0,0] = 8.
        raw['labels'][0,0,12] = 9.
        result = probe.decode_outputs(raw,100,200)
        self.assertEqual([x['class_id'] for x in result],[16])

    def test_invalid_output_names_shapes_types_and_nan_rejected(self):
        for mutate in (lambda x:x.update(extra=x['dets']), lambda x:x.update(labels=x['dets']),
                       lambda x:x.update(dets=x['dets'].astype(np.float64)),
                       lambda x:x['labels'].__setitem__((0,0,1),float('nan')),
                       lambda x:x['dets'].__setitem__((0,0,2),-1)):
            raw = self.raw()
            mutate(raw)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                probe.decode_outputs(raw,100,200)

    def test_bad_threshold_topk_and_dimensions_rejected(self):
        for kwargs in ({'threshold':float('nan')},{'threshold':True},{'threshold':1.1},{'top_k':0},{'top_k':301},{'top_k':True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                probe.decode_outputs(self.raw(),100,200,**kwargs)
        with self.assertRaises(ValueError):
            probe.decode_outputs(self.raw(),0,200)

    def test_clipping_and_completely_outside_rectangles(self):
        raw = self.raw()
        raw['dets'][0,0] = [0.,0.,.3,.3]
        self.assertEqual(probe.decode_outputs(raw,100,200)[0]['box'][:2],[0.,0.])
        raw['dets'][0,0] = [-2.,-2.,.1,.1]
        self.assertEqual(probe.decode_outputs(raw,100,200),[])

    def test_sdk_sparse_mapping_and_array_validation(self):
        sdk = SimpleNamespace(class_id=np.array([18,90]), confidence=np.array([.8,.9]),
                              xyxy=np.array([[0,0,10,10],[5,5,20,20]],dtype=np.float32))
        self.assertEqual([x['class_id'] for x in probe.sdk_predictions(sdk,100,200)],[16,79])
        sdk.class_id = np.array([18.5,90.])
        with self.assertRaises(ValueError):
            probe.sdk_predictions(sdk,100,200)

    def test_bidirectional_parity_detects_extra_missing_and_duplicate_predictions(self):
        row = {'class_id':16,'confidence':.8,'box':[1,2,10,20]}
        self.assertEqual(probe.compare_predictions([row],[row])['directional_strong_matches'],2)
        for candidate in ([],[row,row],[{**row,'class_id':1}],[{**row,'confidence':.5}],[{**row,'box':[20,20,30,30]}]):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                probe.compare_predictions([row],candidate)
        self.assertIsNone(probe.compare_predictions([],[])['minimum_iou'])

    def acquisition(self, temporary, body=b'checkpoint', length=None, md5=None, get_body=None, get_etag='publisher-object', get_url=None):
        size = len(body) if length is None else length
        digest = hashlib.md5(body).hexdigest() if md5 is None else md5
        patches = [patch.object(probe,'ASSETS',Path(temporary)),patch.object(probe,'ASSET_BYTES',size),
                   patch.object(probe,'ASSET_CAP',100),patch.object(probe,'ASSET_MD5',digest)]
        def open_response(request, timeout):
            return Response(b'',size) if hasattr(request,'get_method') and request.get_method()=='HEAD' else Response(
                body if get_body is None else get_body,size,etag=get_etag,url=get_url)
        return patches,open_response

    def test_query_permutation_is_not_prediction_identity(self):
        raw = self.raw()
        raw['dets'] = np.concatenate([raw['dets'],np.array([[[.2,.2,.1,.1]]],dtype=np.float32)],axis=1)
        raw['labels'] = np.concatenate([raw['labels'],np.full((1,1,91),-20.,dtype=np.float32)],axis=1)
        raw['labels'][0,1,90] = 2.
        permuted = {key:value[:,::-1].copy() for key,value in raw.items()}
        check = probe.compare_predictions(probe.decode_outputs(raw,100,200),
                                          probe.decode_outputs(permuted,100,200),minimum=.35)
        self.assertEqual(check['directional_strong_matches'],4)

    def test_native_baseline_accepts_blank_fallback_but_rejects_real_fallback(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            csv_path = Path(temporary)/'detections.csv'
            csv_path.write_text('class_id,confidence,left,top,right,bottom\n0,0.9,0,0,10,10\n',encoding='utf-8')
            for fallback,raises in (('',False),('CPU used instead of requested provider',True)):
                process = SimpleNamespace(returncode=0,stderr='',stdout='Execution provider: CPU\nFallback: '+fallback+'\n')
                with patch.object(probe,'digest',return_value='unchanged'),patch.object(subprocess,'run',return_value=process):
                    if raises:
                        with self.assertRaises(RuntimeError):
                            probe.baseline_predictions(__file__,__file__,csv_path,'small')
                    else:
                        self.assertEqual(probe.baseline_predictions(__file__,__file__,csv_path,'small')['execution']['Fallback'],'')

    def test_bounded_acquisition_verified_and_reused_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            patches,opener = self.acquisition(temporary)
            with patches[0],patches[1],patches[2],patches[3]:
                receipt = probe.acquire_asset(temporary,opener)
                self.assertEqual(receipt['sha256'],hashlib.sha256(b'checkpoint').hexdigest())
                self.assertEqual(probe.acquire_asset(temporary,lambda *a,**kw: self.fail('Unexpected download')),receipt)
                self.assertFalse(list(Path(temporary).glob('*.partial')))

    def test_oversize_and_truncation_preserve_diagnostics_not_final_checkpoint(self):
        for length,body in ((101,b'checkpoint'),(10,b'short')):
            with tempfile.TemporaryDirectory() as temporary:
                patches,opener = self.acquisition(temporary,length=length,get_body=body)
                with patches[0],patches[1],patches[2],patches[3],self.assertRaises(ValueError):
                    probe.acquire_asset(temporary,opener)
                self.assertFalse((Path(temporary)/probe.ASSET_NAME).exists())

    def test_checksum_redirect_and_object_change_rejected(self):
        for kwargs in ({'md5':'wrong'},{'get_etag':'changed'},{'get_url':'https://example.invalid/changed'}):
            with tempfile.TemporaryDirectory() as temporary:
                patches,opener = self.acquisition(temporary,**kwargs)
                with patches[0],patches[1],patches[2],patches[3],self.assertRaises(ValueError):
                    probe.acquire_asset(temporary,opener)
                self.assertFalse((Path(temporary)/probe.ASSET_NAME).exists())

    def test_changed_or_unreceipted_existing_assets_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            patches,opener = self.acquisition(temporary)
            with patches[0],patches[1],patches[2],patches[3]:
                probe.acquire_asset(temporary,opener)
                target = Path(temporary)/probe.ASSET_NAME
                target.write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    probe.acquire_asset(temporary,opener)
                self.assertEqual(target.read_bytes(),b'changed')

    def test_output_scoping_and_existing_runs_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(probe,'OUTPUTS',Path(temporary)):
            for name in (Path(temporary),Path(temporary).parent/'outside-probe'):
                with self.assertRaises(ValueError):
                    probe.new_run(name)
            output = Path(temporary)/'run-1'
            probe.new_run(output)
            with self.assertRaises(FileExistsError):
                probe.new_run(output)

    def test_readonly_comparison_escapes_labels_and_restricts_local_image_paths(self):
        row = {'class_id':0,'confidence':.8,'box':[0,0,10,10]}
        svg = review.prediction_svg('0123456789abcdef',100,200,[row],['<script>alert(1)</script>'])
        self.assertNotIn('<script>',svg)
        self.assertIn('&lt;script&gt;',svg)
        self.assertIn('inputs/0123456789abcdef.png',svg)
        with self.assertRaises(ValueError):
            review.prediction_svg('../elsewhere',100,200,[row],['person'])

    def review_fixture(self,run):
        report = {'status':'completed','sdk_and_onnx_cpu_parity_passed':True,
            'approved_for_application':False,'training_performed':False,'accuracy_evaluated':False,
            'native_rf_adapter_implemented':False,'directml_evaluated':False,'contract':probe.contract(),
            'images':[{'image_id':'0123456789abcdef','width':100,'height':200,
                       'rf_onnx_predictions':[{'class_id':0,'confidence':.8,'box':[0,0,10,10]}]}]}
        (run/'experiment.json').write_text(json.dumps(report),encoding='utf-8')
        return report

    def test_comparison_is_offline_readonly_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(review,'OUTPUTS',Path(temporary)):
            run = Path(temporary)/'run';run.mkdir();self.review_fixture(run)
            target = review.make_review(run)
            content = target.read_text(encoding='utf-8')
            self.assertNotIn('<script',content)
            self.assertNotIn('http',content)
            self.assertIn('not corrected annotations',content)
            with self.assertRaises(FileExistsError):
                review.make_review(run)

    def test_comparison_rejects_failed_or_adopted_experiment(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(review,'OUTPUTS',Path(temporary)):
            run = Path(temporary)/'run';run.mkdir()
            for changes in ({'status':'failed'},{'approved_for_application':True},{'accuracy_evaluated':True}):
                report = self.review_fixture(run);report.update(changes)
                (run/'experiment.json').write_text(json.dumps(report),encoding='utf-8')
                with self.assertRaises(ValueError):
                    review.make_review(run)
                self.assertFalse((run/'comparison.html').exists())


if __name__ == '__main__':
    unittest.main()
