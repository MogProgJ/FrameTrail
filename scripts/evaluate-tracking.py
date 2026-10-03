"""Score native track/event CSV against reviewed source-frame labels. Local developer tooling."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def iou(a, b):
    area = max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area
    return area/union if union else 0


def validate(document):
    if document.get('schema') != 1 or not isinstance(document.get('frames'), list) or not document['frames']:
        raise ValueError('Expected schema 1 and nonempty labelled frames')
    width, height = document.get('width'), document.get('height')
    if any(type(v) is not int or v <= 0 for v in (width, height)):
        raise ValueError('Positive source dimensions required')
    sequences = set()
    classes = {}
    for frame in document['frames']:
        seq = frame.get('sequence')
        if type(seq) is not int or seq < 1 or seq in sequences or type(frame.get('complete')) is not bool:
            raise ValueError('Unique source sequences >=1 and explicit frame completeness required; frame zero seeds tracking')
        sequences.add(seq)
        identities = set()
        for item in frame['objects']:
            identity, cls, box = item['object_id'], item['class_id'], item['box']
            if (not isinstance(identity, str) or not identity or identity in identities or type(cls) is not int or not 0 <= cls < 80 or
                    len(box) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in box) or
                    not 0 <= box[0] < box[2] <= width or not 0 <= box[1] < box[3] <= height):
                raise ValueError('Invalid reference identity, class or original-pixel box')
            if identity in classes and classes[identity] != cls:
                raise ValueError('Reference identity changed class; label shot-local identities consistently')
            identities.add(identity)
            classes[identity] = cls
    events = document.get('events')
    if (not isinstance(events, dict) or type(events.get('complete')) is not bool or
            any(type(events.get(k)) is not int for k in ('start_sequence', 'end_sequence')) or
            not 1 <= events['start_sequence'] <= events['end_sequence']):
        raise ValueError('Explicit reviewed event range and completeness required')
    seen = set()
    for event in events['items']:
        if (not isinstance(event['event_id'], str) or not event['event_id'] or event['event_id'] in seen or
                event['object_id'] not in classes or type(event['sequence']) is not int or
                not events['start_sequence'] <= event['sequence'] <= events['end_sequence'] or
                event['direction'] not in ('negative_to_positive', 'positive_to_negative')):
            raise ValueError('Invalid reference event')
        seen.add(event['event_id'])
    return document


def frame_matches(truth, predictions, threshold):
    """Maximum-cardinality same-class IoU matching; deterministic descending-IoU edges."""
    edges = [[j for _, j in sorted(((iou(p['box'], t['box']), j) for j, t in enumerate(truth)
              if p['class_id'] == t['class_id'] and iou(p['box'], t['box']) >= threshold), reverse=True)] for p in predictions]
    owner = {}
    def augment(prediction, visited):
        for reference in edges[prediction]:
            if reference in visited:
                continue
            visited.add(reference)
            if reference not in owner or augment(owner[reference], visited):
                owner[reference] = prediction
                return True
        return False
    for prediction in sorted(range(len(predictions)), key=lambda i: (-predictions[i]['confidence'], predictions[i]['track_id'])):
        augment(prediction, set())
    return [(truth[reference], predictions[prediction]) for reference, prediction in sorted(owner.items())]


def score(document, tracks, predicted_events, threshold=.5, tolerance=2):
    validate(document)
    if not math.isfinite(threshold) or not 0 < threshold <= 1 or type(tolerance) is not int or tolerance < 0:
        raise ValueError('Invalid match threshold or source-frame event tolerance')
    history, associations, frames = {}, {}, []
    for frame in sorted(document['frames'], key=lambda f: f['sequence']):
        seq = frame['sequence']
        predictions = [p for p in tracks if p['sequence'] == seq]
        if len({p['track_id'] for p in predictions}) != len(predictions):
            raise ValueError('Track reused twice in one source frame')
        matches = frame_matches(frame['objects'], predictions, threshold)
        for reference, prediction in matches:
            history.setdefault(reference['object_id'], []).append((seq, prediction['track_id']))
            associations.setdefault(prediction['track_id'], set()).add(reference['object_id'])
        frames.append({'sequence': seq, 'targets': len(frame['objects']), 'matched': len(matches),
                       'missed': len(frame['objects'])-len(matches), 'predictions': len(predictions),
                       'false_positives': len(predictions)-len(matches) if frame['complete'] else None,
                       'complete': frame['complete']})
    identities = [{'object_id': identity, 'matched_samples': len(values), 'track_ids': sorted({p for _, p in values}),
                   'id_changes': sum(a[1] != b[1] for a, b in zip(values, values[1:]))} for identity, values in sorted(history.items())]
    refs = document['events']
    candidates = []
    classes = {o['object_id']: o['class_id'] for f in document['frames'] for o in f['objects']}
    for index, ref in enumerate(refs['items']):
        anchors = [(f['sequence'], o) for f in document['frames'] for o in f['objects']
                   if o['object_id'] == ref['object_id'] and abs(f['sequence']-ref['sequence']) <= tolerance]
        if not anchors:
            raise ValueError('Each reference event needs an identity box within its frame tolerance')
        ids = {track for seq, track in history.get(ref['object_id'], []) if abs(seq-ref['sequence']) <= tolerance}
        for j, event in enumerate(predicted_events):
            distance = abs(event['sequence']-ref['sequence'])
            if (refs['start_sequence'] <= event['sequence'] <= refs['end_sequence'] and distance <= tolerance and event['track_id'] in ids and event['class_id'] == classes[ref['object_id']]
                    and event['direction'] == ref['direction']):
                candidates.append((distance, index, j))
    # Augmenting paths ensure a duplicate cannot consume another event's only candidate.
    event_edges = {i: [] for i in range(len(refs['items']))}
    for _, ref, prediction in sorted(candidates):
        event_edges[ref].append(prediction)
    event_owner = {}
    def event_augment(reference, visited):
        for prediction in event_edges[reference]:
            if prediction in visited:
                continue
            visited.add(prediction)
            if prediction not in event_owner or event_augment(event_owner[prediction], visited):
                event_owner[prediction] = reference
                return True
        return False
    for reference in event_edges:
        event_augment(reference, set())
    reviewed = [j for j, event in enumerate(predicted_events) if refs['start_sequence'] <= event['sequence'] <= refs['end_sequence']]
    unmatched = [j for j in reviewed if j not in event_owner]
    targets, matched = sum(f['targets'] for f in frames), sum(f['matched'] for f in frames)
    return {'targets': targets, 'matched': matched, 'missed': targets-matched, 'target_recall': matched/targets if targets else None,
            'false_positives': sum(f['false_positives'] for f in frames) if all(f['complete'] for f in frames) else None,
            'id_changes_between_labelled_matches': sum(i['id_changes'] for i in identities), 'identities': identities,
            'track_reuse_hints': [{'track_id': t, 'object_ids': sorted(ids)} for t, ids in sorted(associations.items()) if len(ids) > 1],
            'frames': frames, 'events': {'targets': len(refs['items']), 'matched': len(event_owner), 'missed': len(refs['items'])-len(event_owner),
                'reviewed_predictions': len(reviewed), 'unmatched_prediction_hints': len(unmatched),
                'false_positives': len(unmatched) if refs['complete'] else None,
                'duplicate_hints': sum(any(j == prediction for _, _, prediction in candidates) for j in unmatched),
                'complete': refs['complete'], 'source_frame_tolerance': tolerance}}


def read_csv(path, events=False):
    result = []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader=csv.DictReader(stream)
        required={'sequence','track_id','class_id','direction'} if events else {'sequence','track_id','class_id','confidence','left','top','right','bottom'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Native CSV headers missing')
        for row in reader:
            item = {'sequence': int(row['sequence']), 'track_id': int(row['track_id']), 'class_id': int(row['class_id'])}
            if item['sequence'] < 1 or item['track_id'] < 1 or not 0 <= item['class_id'] < 80:
                raise ValueError('Invalid native row identity')
            if events:
                item['direction'] = row['direction']
                if item['direction'] not in ('negative_to_positive', 'positive_to_negative'):
                    raise ValueError('Invalid event direction')
            else:
                item.update(confidence=float(row['confidence']), box=[float(row[k]) for k in ('left', 'top', 'right', 'bottom')])
                b = item['box']
                if not all(math.isfinite(v) for v in [*b, item['confidence']]) or not 0 <= item['confidence'] <= 1 or not b[0] < b[2] or not b[1] < b[3]:
                    raise ValueError('Invalid native box/confidence')
            result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'tracks', 'events', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--event-tolerance', type=int, default=2)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    result = score(manifest, read_csv(args.tracks), read_csv(args.events, True), tolerance=args.event_tolerance)
    result.update(schema=1, hashes={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in
                  [('manifest', args.manifest), ('tracks', args.tracks), ('events', args.events)]},
                  notes='Sparse reviewed labels only. ID changes are between labelled matches, not HOTA/IDF1/MOTA. Partial labels cannot establish precision or false events. CSV hashes do not prove source/model provenance; preserve the native command, source/model hashes and logs separately.')
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(f"Matched {result['matched']}/{result['targets']} targets; ID changes between labelled matches: {result['id_changes_between_labelled_matches']}")


if __name__ == '__main__':
    main()
