"""RF prelabel catalogue integrity and human-adoption history, no inference/network."""
import copy
import json
from pathlib import Path
import sys
import shutil
import subprocess
import importlib.util
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import annotation_review as review
import rfdetr_annotations as rf
from training_data import digest,read_json,write_json
import test_annotation_review as annotation_tests
repair_spec=importlib.util.spec_from_file_location('repair_saves',ROOT/'scripts/repair-annotation-saves.py')
repair_saves=importlib.util.module_from_spec(repair_spec);repair_spec.loader.exec_module(repair_saves)


class RFCatalogueTests(unittest.TestCase):
    def setUp(self):
        annotation_tests.AnnotationTests.setUp(self)
        self.pack={'schema':1,'status':'completed','purpose':'rfdetr-annotation-proposals-only',
            'approved_for_training':False,'source_manifest_sha256':self.seed['source_manifest_sha256'],
            'pack_id':'a'*16,'model_sha256':'b'*64,'contract':rf.contract(),
            'threshold':.35,'backend':'CPUExecutionProvider','images':[]}
        image=self.seed['images'][0]
        candidates=[]
        for number,cid in enumerate((0,65),1):  # person and remote (no exact Open Images canonical match)
            cls=self.pack['contract']['classes'][cid]
            candidates.append({'id':f"rf-{'a'*16}-{image['id']}-{number}",'name':cls['name'],
                'raw_slot':cls['raw_slot'],'canonical_id':cid,'raw_id':rf.mapped_raw(cid),
                'box':[1,2,10,20],'confidence':.9})
        self.pack['images']=[{'image_id':image['id'],'sha256':image['sha256'],'width':20,'height':30,'candidates':candidates}]
        self.image_id=image['id']

    def adopt(self,number=0):
        obj=rf.proposal_object(self.pack,self.image_id,self.pack['images'][0]['candidates'][number]['id'])
        review.event(self.state,self.image_id,'proposal-add',obj['id'],obj,'human',self.pack)
        return obj

    def attach(self):
        write_json(self.workspace/'rf-proposals.json',self.pack)
        meta=read_json(self.workspace/'workspace.json')
        meta['rfdetr_proposals']={'path':'rf-proposals.json','sha256':digest(self.workspace/'rf-proposals.json')}
        write_json(self.workspace/'workspace.json',meta)

    def test_exact_mapping_and_unsupported_categories_not_guessed(self):
        rf.validate_pack(self.pack,self.seed)
        self.assertEqual(rf.mapped_raw(0),381)
        self.assertIsNone(rf.mapped_raw(65))
        self.assertFalse(self.pack['approved_for_training'])

    def test_changed_class_identity_geometry_score_contract_and_image_rejected(self):
        for mutate in (lambda x:x.update(approved_for_training=True),lambda x:x.update(status='running'),
            lambda x:x.update(source_manifest_sha256='wrong'),lambda x:x.update(threshold=.1),
            lambda x:x['images'][0].update(sha256='wrong'),
            lambda x:x['images'][0]['candidates'][0].update(raw_id=57),
            lambda x:x['images'][0]['candidates'][0].update(raw_id=True),
            lambda x:x['images'][0]['candidates'][0].update(name='fox'),
            lambda x:x['images'][0]['candidates'][0].update(raw_slot=0),
            lambda x:x['images'][0]['candidates'][0].update(confidence=float('nan')),
            lambda x:x['images'][0]['candidates'][0].update(box=[0,0,21,20])):
            bad=copy.deepcopy(self.pack);mutate(bad)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):rf.validate_pack(bad,self.seed)

    def test_adoption_is_pending_exact_and_preserves_old_records(self):
        prior=copy.deepcopy(self.state['images'][0]['objects']);obj=self.adopt()
        review.validate_state(self.seed,self.state,self.pack)
        self.assertEqual(self.state['images'][0]['objects'][:-1],prior)
        self.assertEqual(obj['status'],'pending');self.assertEqual(obj['origin']['model'],'RF-DETR Small')
        with self.assertRaises(ValueError):review.validate_state(self.seed,self.state)
        with self.assertRaises(ValueError):self.adopt()

    def test_catalogue_proposal_cannot_be_preconfirmed_or_forged(self):
        for fields in ({'status':'confirmed'},{'box':[2,2,10,20]},{'raw_id':57}):
            obj=rf.proposal_object(self.pack,self.image_id,self.pack['images'][0]['candidates'][0]['id']);obj.update(fields)
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                review.event(self.state,self.image_id,'proposal-add',obj['id'],obj,'human',self.pack)
        self.assertEqual(self.state['events'],[])

    def test_confirmation_and_updates_preserve_model_provenance(self):
        obj=self.adopt();after=copy.deepcopy(obj);after.update(status='confirmed',box=[2,3,11,21])
        review.event(self.state,self.image_id,'update',obj['id'],after,'human',self.pack)
        review.validate_state(self.seed,self.state,self.pack)
        after['origin']['confidence']=.99
        with self.assertRaises(ValueError):review.event(self.state,self.image_id,'update',obj['id'],after,'human',self.pack)

    def test_outside_vocabulary_rf_proposal_is_observation_and_not_export_target(self):
        obj=self.adopt(1);self.assertIn('label',obj);self.assertNotIn('raw_id',obj)
        after=copy.deepcopy(obj);after['status']='confirmed'
        review.event(self.state,self.image_id,'observation-update',obj['id'],after,'human',self.pack)
        review.validate_state(self.seed,self.state,self.pack);self.attach()
        write_json(self.workspace/'reviewed.json',self.state)
        review.export_draft(self.workspace,self.workspace/'reviewed.json',self.root/'export')
        coco=read_json(self.root/'export/draft-coco.json');self.assertEqual(len(coco['annotations']),1)
        self.assertEqual(read_json(self.root/'export/unsupported-observations.json')['images'][0]['observations'][0]['origin']['model'],'RF-DETR Small')
        bad=copy.deepcopy(after);bad['origin']['confidence']=.1
        with self.assertRaises(ValueError):review.event(self.state,self.image_id,'observation-update',obj['id'],bad,'human',self.pack)

    def test_model_observation_cannot_impersonate_manual_add(self):
        obj=rf.proposal_object(self.pack,self.image_id,self.pack['images'][0]['candidates'][1]['id'])
        with self.assertRaises(ValueError):review.event(self.state,self.image_id,'observation-add',obj['id'],obj,'human')

    def test_workspace_catalogue_checksum_and_path_are_enforced(self):
        self.attach();self.assertEqual(review.load_proposals(self.workspace,self.seed),self.pack)
        (self.workspace/'rf-proposals.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):review.load_proposals(self.workspace,self.seed)

    def test_editor_preserves_seed_and_escapes_payload_text(self):
        self.pack['limits']='</script><script>bad</script>'
        target=self.workspace/'rf-editor.html';review.render_editor(self.seed,self.state,target,self.pack)
        content=target.read_text(encoding='utf-8');self.assertIn('id="rf-list"',content)
        self.assertNotIn('</script><script>bad</script>',content)
        self.assertEqual(read_json(self.workspace/'seed.json'),self.seed)
        with self.assertRaises(FileExistsError):review.render_editor(self.seed,self.state,target,self.pack)

    def test_unselected_proposals_are_not_exported_as_training_labels(self):
        self.attach();review.export_draft(self.workspace,self.workspace/'annotations.json',self.root/'export')
        self.assertEqual(len(read_json(self.root/'export/draft-coco.json')['annotations']),1)
        self.assertEqual(read_json(self.root/'export/unsupported-observations.json')['images'][0]['observations'],[])

    def test_javascript_review_actions_replay_in_python(self):
        review.event(self.state,self.image_id,'add','manual-person-match',
            {'id':'manual-person-match','raw_id':381,'box':[1,2,10,20],'status':'confirmed',
             'note':'Prior human correction','origin':{'kind':'manual'}},'prior-human')
        node=shutil.which('node')
        bundled=Path(r'C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
        node=node or (str(bundled) if bundled.is_file() else None)
        if not node:self.skipTest('Node unavailable')
        result=subprocess.run([node,str(ROOT/'tests/test_rfdetr_editor.cjs')],
            input=json.dumps({'seed':self.seed,'state':self.state,'proposals':self.pack}),text=True,
            encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(result.stdout);review.validate_state(self.seed,state,self.pack)
        self.assertEqual(state['images'][0]['objects'][0]['status'],'pending')
        self.assertEqual(state['images'][0]['observations'][0]['status'],'confirmed')
        self.assertTrue(any(x['kind']=='proposal-add' for x in state['events']))

    def matching_target(self,observation=False):
        target={'id':'observation-matching-remote' if observation else 'manual-matching-person',
            'box':[1,2,10,20],'status':'pending','note':'Prior human save',
            'origin':{'kind':'manual-observation' if observation else 'manual'}}
        target['label' if observation else 'raw_id']='remote' if observation else 381
        review.event(self.state,self.image_id,'observation-add' if observation else 'add',target['id'],target,'human',self.pack)
        return target

    def test_linked_proposal_cannot_reactivate_or_edit_geometry(self):
        obj=self.adopt();target=self.matching_target()
        linked=copy.deepcopy(obj);linked.update(status='rejected',linked_to=target['id'],note='Applied to matching target')
        review.event(self.state,self.image_id,'proposal-link',obj['id'],linked,'human',self.pack)
        review.validate_state(self.seed,self.state,self.pack)
        for fields in ({'status':'confirmed'},{'status':'pending'},{'box':[0,0,10,20]},{'linked_to':'publisher-1'}):
            bad=copy.deepcopy(linked);bad.update(fields)
            with self.subTest(fields=fields),self.assertRaises(ValueError):review.event(self.state,self.image_id,'update',obj['id'],bad,'human',self.pack)

    def test_link_refuses_missing_wrong_category_self_or_unchecked_catalogue(self):
        obj=self.adopt();self.matching_target()
        for target in ('missing','publisher-1',obj['id']):
            after=copy.deepcopy(obj);after.update(status='rejected',linked_to=target,note='Applied')
            with self.subTest(target=target),self.assertRaises(ValueError):review.event(self.state,self.image_id,'proposal-link',obj['id'],after,'human',self.pack)
        after=copy.deepcopy(obj);after.update(status='rejected',linked_to='manual-matching-person',note='Applied')
        with self.assertRaises(ValueError):review.event(self.state,self.image_id,'proposal-link',obj['id'],after,'human')

    def test_linked_observation_cannot_become_training_target_or_reactivate(self):
        obj=self.adopt(1);target=self.matching_target(True)
        linked=copy.deepcopy(obj);linked.update(status='rejected',linked_to=target['id'],note='Applied to existing observation')
        review.event(self.state,self.image_id,'proposal-link',obj['id'],linked,'human',self.pack)
        review.validate_state(self.seed,self.state,self.pack)
        bad=copy.deepcopy(linked);bad['status']='confirmed'
        with self.assertRaises(ValueError):review.event(self.state,self.image_id,'observation-update',obj['id'],bad,'human',self.pack)

    def test_save_migration_requires_explicit_approval_and_new_output(self):
        self.attach();path=self.workspace/'resume.json'
        with self.assertRaises(ValueError):repair_saves.repair(self.workspace,self.workspace/'annotations.json',path)
        self.assertFalse(path.exists())
        with self.assertRaises(ValueError):repair_saves.repair(self.workspace,self.workspace/'annotations.json',self.workspace/'annotations.json',True)

    def test_migration_confirms_only_user_touched_pending_and_preserves_geometry(self):
        target=self.matching_target();self.attach()
        input_path=self.workspace/'user-saved.json';write_json(input_path,self.state);before=digest(input_path)
        result=repair_saves.repair(self.workspace,input_path,self.workspace/'resume.json',True)
        repaired=read_json(self.workspace/'resume.json');review.validate_state(self.seed,repaired,self.pack)
        self.assertEqual(digest(input_path),before);self.assertEqual(len(result['newly_confirmed']),1)
        self.assertEqual(repaired['images'][0]['objects'][0]['status'],'pending')
        self.assertEqual(repaired['images'][0]['objects'][-1]['status'],'confirmed')
        self.assertEqual(repaired['images'][0]['objects'][-1]['box'],target['box'])
        self.assertEqual(repaired['images'][0]['review'],self.state['images'][0]['review'])
        self.assertEqual(repaired['events'][:len(self.state['events'])],self.state['events'])

    def test_legacy_reactivated_duplicate_is_linked_not_confirmed(self):
        with patch.object(review,'utc',return_value='2026-10-08T18:00:00+00:00'):
            obj=self.adopt();target=self.matching_target()
            rejected=copy.deepcopy(obj);rejected.update(status='rejected',note='Not a new target: user applied this suggestion to existing box '+target['id']+'. Original prediction preserved.')
            review.event(self.state,self.image_id,'update',obj['id'],rejected,'human',self.pack)
            review.event(self.state,self.image_id,'update',target['id'],target,'human',self.pack)
            reopened=copy.deepcopy(rejected);reopened['status']='pending'
            review.event(self.state,self.image_id,'update',obj['id'],reopened,'human',self.pack)
        self.attach();write_json(self.workspace/'user-saved.json',self.state)
        result=repair_saves.repair(self.workspace,self.workspace/'user-saved.json',self.workspace/'resume.json',True)
        repaired=read_json(self.workspace/'resume.json');review.validate_state(self.seed,repaired,self.pack)
        rf_record=next(x for x in repaired['images'][0]['objects'] if x['id']==obj['id'])
        self.assertEqual(rf_record['status'],'rejected');self.assertEqual(rf_record['linked_to'],target['id'])
        self.assertEqual(len(result['newly_confirmed']),1);self.assertEqual(len(result['linked_proposals']),1)


if __name__=='__main__':unittest.main()
