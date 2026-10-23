"""Explicit user-authorized save=confirm migration into a NEW JSON; originals/history remain intact."""
import argparse
import copy
import json
from pathlib import Path
import re

from annotation_review import event, load_checked, load_proposals, summary, validate_state
from training_data import digest, read_json, write_json


def legacy_links(state, pack):
    links = {}
    for change,next_change in zip(state['events'],state['events'][1:]):
        after=change['after']
        if change['kind'] not in ('update','observation-update') or after.get('status')!='rejected' or after.get('origin',{}).get('pack_id')!=pack['pack_id']:
            continue
        match=re.fullmatch(r'Not a new target: user applied this suggestion to existing box ([a-zA-Z0-9-]+)\. Original prediction preserved\.',after.get('note',''))
        if not match or next_change['kind'] not in ('update','observation-update') or next_change['image_id']!=change['image_id'] or next_change['object_id']!=match[1] or next_change['at']!=change['at'] or next_change['actor']!=change['actor'] or next_change['after']['box']!=after['box']:
            continue
        key=(change['image_id'],change['object_id'])
        if key in links and links[key]!=match[1]:
            raise ValueError('Ambiguous historical RF link; do not guess its target')
        links[key]=match[1]
    return links


def repair(workspace, annotations, output, confirm_user_saved=False):
    if confirm_user_saved is not True:
        raise ValueError('Requires explicit approval with --confirm-user-saved; never silently infer confirmation')
    workspace,annotations=Path(workspace).resolve(strict=True),Path(annotations).resolve(strict=True)
    output=Path(output).resolve()
    if output.parent!=workspace or output.exists():
        raise ValueError('Choose a NEW JSON file directly in this RF workspace')
    receipt=output.with_suffix('.repair.json')
    if receipt.exists():
        raise FileExistsError('Existing repair receipt is preserved')
    input_hash=digest(annotations)
    _,state=load_checked(workspace,annotations)
    seed=read_json(workspace/'seed.json');pack=load_proposals(workspace,seed)
    if pack is None:raise ValueError('RF repair requires its original checked catalogue')
    baseline=read_json(workspace/'annotations.json')
    validate_state(seed,baseline,pack)
    if state['events'][:len(baseline['events'])]!=baseline['events']:
        raise ValueError('Supplied history does not extend this exact prepared baseline')
    original=copy.deepcopy(state)
    human_changes=state['events'][len(baseline['events']):]
    if any(e['actor'].startswith('assistant-') for e in human_changes):
        raise ValueError('Mixed assistant/user history requires a scoped review before automatic status migration')
    touched={(e['image_id'],e['object_id']) for e in human_changes if e['kind'] in ('add','update','observation-add','observation-update','proposal-add')}
    actor='user-authorized-save-confirm-migration'
    linked=legacy_links(state,pack)
    linked_rows=[];confirmed_rows=[]
    for (image_id,object_id),target_id in linked.items():
        image=next(x for x in state['images'] if x['id']==image_id)
        records=image['objects']+image.get('observations',[])
        obj=next(x for x in records if x['id']==object_id)
        target=next(x for x in records if x['id']==target_id)
        if obj.get('linked_to')==target_id:continue
        after=copy.deepcopy(obj);after['status']='rejected';after['linked_to']=target_id
        after['note']='Applied to existing saved box '+target_id+'. Linked duplicate stays rejected; user-authorized repair preserves the original prediction and prior history.'
        event(state,image_id,'proposal-link',obj['id'],after,actor,pack)
        linked_rows.append({'image':image['number'],'proposal_id':object_id,'target_id':target_id,'was_active':obj['status']!='rejected'})
    for image in state['images']:
        for obj in list(image['objects']+image.get('observations',[])):
            if obj['status']=='pending' and not obj.get('linked_to') and (image['id'],obj['id']) in touched:
                after=copy.deepcopy(obj);after['status']='confirmed'
                after['note']=obj['note']+'\nConfirmed under the user\'s explicit 8 October 2026 instruction: saved box changes and RF-to-existing-box updates count as confirmation.'
                event(state,image['id'],'observation-update' if 'label' in obj else 'update',obj['id'],after,actor,pack)
                confirmed_rows.append({'image':image['number'],'id':obj['id'],'observation':'label' in obj})
    validate_state(seed,state,pack)
    if state['events'][:len(original['events'])]!=original['events'] or digest(annotations)!=input_hash:
        raise ValueError('Input/history changed during migration')
    for before,after in zip(original['images'],state['images']):
        if before['review']!=after['review']:
            raise ValueError('Box confirmation must not change image/rights approval')
        old={x['id']:x for x in before['objects']+before.get('observations',[])}
        for obj in after['objects']+after.get('observations',[]):
            if obj['box']!=old[obj['id']]['box'] or obj.get('raw_id')!=old[obj['id']].get('raw_id') or obj.get('label')!=old[obj['id']].get('label') or obj['origin']!=old[obj['id']]['origin']:
                raise ValueError('Migration must not alter geometry, labels or source provenance')
    write_json(output,state)
    report={'schema':1,'purpose':'explicit-user-authorized-save-confirm-repair','input_sha256':input_hash,
        'output_sha256':digest(output),'preserved_input_events':len(original['events']),
        'linked_proposals':linked_rows,'newly_confirmed':confirmed_rows,'summary':summary(state),
        'limits':'User-approved status correction only. No independent visual accuracy, whole-image coverage, rights clearance or training approval.'}
    write_json(receipt,report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','annotations','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--confirm-user-saved',action='store_true')
    args=parser.parse_args()
    try:
        result=repair(args.workspace,args.annotations,args.output,args.confirm_user_saved)
        print(json.dumps({'newly_confirmed':len(result['newly_confirmed']),'linked_proposals':len(result['linked_proposals']),
                          'summary':result['summary'],'output':str(args.output)},indent=2))
    except (ValueError,OSError,KeyError,StopIteration) as error:parser.exit(1,f'Annotation repair error: {error}\n')
