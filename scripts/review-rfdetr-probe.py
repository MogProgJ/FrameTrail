"""Render a read-only local prediction comparison, never an annotation or accuracy report."""
import argparse
import csv
import html
import json
from pathlib import Path
import re

from rfdetr_probe import OUTPUTS
from training_data import valid_box


def prediction_svg(image_id, width, height, predictions, names):
    if not re.fullmatch('[0-9a-f]{16}', image_id) or type(width) is not int or type(height) is not int or min(width,height) <= 0:
        raise ValueError('Invalid local image identity/dimensions')
    if len(predictions) > 1000 or len(names) != len(predictions):
        raise ValueError('Invalid bounded prediction display')
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Unverified model predictions">',
             f'<image href="inputs/{image_id}.png" width="{width}" height="{height}"/>']
    for row,name in zip(predictions,names):
        if not valid_box(row['box'],width,height) or not 0 <= row['confidence'] <= 1:
            raise ValueError('Invalid prediction geometry/confidence')
        left,top,right,bottom = row['box']
        caption = html.escape(f"{name}: {row['confidence']:.3f}")
        parts.append(f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" '
                     f'fill="none" stroke="#ffcf4a" stroke-width="2" vector-effect="non-scaling-stroke"><title>{caption}</title></rect>')
    return '\n'.join(parts)+'</svg>'


def make_review(run):
    run = Path(run).resolve(strict=True)
    if run == OUTPUTS.resolve() or not run.is_relative_to(OUTPUTS.resolve()):
        raise ValueError('Review must stay inside an existing isolated probe run')
    target = run/'comparison.html'
    if target.exists():
        raise FileExistsError('Existing comparison is preserved')
    report = json.loads((run/'experiment.json').read_text(encoding='utf-8'))
    if report.get('status') != 'completed' or report.get('sdk_and_onnx_cpu_parity_passed') is not True or any(
        report.get(key) is not False for key in ('approved_for_application','training_performed','accuracy_evaluated','native_rf_adapter_implemented','directml_evaluated')):
        raise ValueError('Only a completed, unapproved CPU mechanics probe can be displayed')
    if not 1 <= len(report['images']) <= 12:
        raise ValueError('Invalid probe image budget')
    names = {x['canonical_id']:x['name'] for x in report['contract']['classes']}
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>FrameTrail — RF-DETR CPU mechanics comparison</title>',
        '<style>body{font:16px system-ui;margin:24px;background:#eef1f4;color:#17212c}main{max-width:1500px;margin:auto}',
        '.warning{padding:16px;background:#fff0bf;border:1px solid #987000}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}',
        'article{background:white;padding:12px;border-radius:6px}svg{display:block;width:100%;background:#222}li{margin:4px 0}',
        '@media(max-width:900px){.grid{grid-template-columns:1fr}}h2{margin-top:36px}</style><main>',
        '<h1>Pretrained detector comparison — mechanics only</h1>',
        '<p class="warning">These are model guesses, not corrected annotations or ground truth. Six publisher-train photos cannot establish accuracy. '
        'RF-DETR covers 80 COCO classes; Open Images covers 597 canonical classes. More boxes does not mean a better model. '
        'No training, model adoption, native RF-DETR integration or DirectML check has occurred.</p>',
        '<p>Yellow rectangles: predictions at confidence &gt; 0.35. Hover a box for its label/score, or expand the prediction list. '
        'This page is read-only; your annotation editor remains separate. All columns use the same clean derived PNG.</p>',
        '<p>Python/ONNX decoded detections agree on these six inputs. Raw query tensors are <strong>not</strong> positionwise equivalent. '
        'See <a href="experiment.json">the experiment record</a> for deltas, provenance and limits.</p>']
    for image in report['images']:
        image_id = image['image_id']
        columns = [('RF-DETR Small — ONNX CPU',image['rf_onnx_predictions'],[names[x['class_id']] for x in image['rf_onnx_predictions']])]
        for baseline in image.get('baselines',[]):
            profile = baseline['profile']
            if profile not in ('small','openimages') or not re.fullmatch('[0-9a-f]{16}',image_id):
                raise ValueError('Invalid baseline CSV identity')
            with (run/(profile+'-'+image_id+'.csv')).open(encoding='utf-8-sig',newline='') as stream:
                rows = list(csv.DictReader(stream))
            expected = [{'class_id':int(x['class_id']),'confidence':float(x['confidence']),
                         'box':[float(x[key]) for key in ('left','top','right','bottom')]} for x in rows]
            if expected != baseline['predictions']:
                raise ValueError('Baseline CSV changed after the experiment')
            columns.append(('YOLOX-S — native CPU' if profile=='small' else 'Open Images — native CPU',expected,[x['label'] for x in rows]))
        parts.append(f'<h2>{html.escape(image_id)}</h2><div class="grid">')
        for title,predictions,labels in columns:
            svg = prediction_svg(image_id,image['width'],image['height'],predictions,labels)
            parts.append(f'<article><h3>{html.escape(title)}</h3>{svg}<details><summary>{len(predictions)} predictions — not accuracy</summary><ul>')
            parts.extend('<li>'+html.escape(f"{label}: {row['confidence']:.3f}")+'</li>' for row,label in zip(predictions,labels))
            parts.append('</ul></details></article>')
        parts.append('</div>')
    parts.append('</main></html>')
    with target.open('x',encoding='utf-8') as stream:
        stream.write('\n'.join(parts))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True,type=Path)
    args = parser.parse_args()
    try:
        print(make_review(args.run))
    except (OSError,ValueError,KeyError) as error:
        parser.exit(1,f'Comparison error: {error}\n')
