"""Explain audited development results without changing any selection decision."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'DIAGNOSIS.json').read_text());trials=data['trials']
lines=['# Why array7809335 retained its starting model','',
'All four tasks completed normally. The independent local audit replayed all64 validation records and all checkpoint-selection decisions. Best/last tensors confirm that only billboard row133 changed during training; every selected best.pt has exactly the starting model state. Different serialized best.pt hashes reflect task provenance, not four different selected model states.','',
'The retained new-run step0 is **job7805570 selected step100**, preserving the washing-machine gain. Each new task performed1500actual updates before its predeclared no-eligible-gain stop:6000updates and18000presentations across the array.','',
'## What was learned','',
'The billboard row learned the training signal and started detecting known validation targets. It also generated false positives and more predictions on unscored image/class scopes. No tested100-update checkpoint met the unchanged selection rules.','',
'| Trial | Pos:explicit-neg | Learning rate | Max known billboard hits /11 | Final hits /11 | Final measured billboard FP | Final unscored predictions |','|---|---|---|---|---|---|---|']
for r in trials:
    f=r['final'];v=r['variant'];lines.append(f"| {r['index']} | 1:{v['negative_presentations']} | {v['lr']} | {r['max_billboard_hits']} | {f['billboard_known_hits']} | {f['billboard_complete_fp']} | {f['all_unscored_predictions']} |")
lines += ['',
'Current baseline has528 aggregate unscored predictions; the original baseline has525. The +5 guard against either baseline gives an effective cap of530. These unscored predictions are **not measured false positives**: their scopes do not support that judgment. The cap is a conservative drift guard and has not been rewritten after seeing results.','',
'The closest checkpoints were task1/step600 and task3/step200:1/11 billboard hits, zero measured billboard false positives, and531unscored predictions. They missed the guard by one. Later checkpoints showed larger gains but also measured false positives. Washing-machine validation hits stayed8/13 at every inspected point. No regression of those frozen counts was needed to explain rejection.','',
'## What these comparisons support','',
'With the same scheduled positives, more explicit-negative presentations lowered false positives and drift while also reducing the maximum measured billboard gain. Higher learning rate reached its first billboard hit earlier (step200 rather than600), but did not solve the specificity problem. These are four fixed development trajectories, not seed replications or a population-level causal estimate. Only checkpoints every100updates were evaluated; this does not prove that every intermediate optimizer state would fail.','',
'The selected model already passed the prior known-reference retention checks; since none changed, the batch reused its pinned regression scores rather than rerunning identical inference. No new held-out accuracy measurement was obtained. The known references are consumed, and another development experiment does not create independent generalization evidence.','',
'## Local next experiment and efficiency','',
'The transformer/features/boxes are frozen and the trainable final classifier runs after feature extraction. Four training-photo tests showed bitwise-identical live/cached outputs, losses and row gradients. A changed-row probe also preserved features and replayed exact outputs. A first attempt to trim decoder layers exposed FP32 layout differences; its partial cache and failure log are preserved. The replacement cache keeps the complete tensor layout and is checked image by image.','',
'The sibling frozen-head-cpu-7809335-20261018-v1 folder contains a predeclared local diagnostic using the same55training photos and135development photos. Four regularized final-row fits will be trained only on geometry-covered known-positive query features and explicitly absent query features. All four fits precede validation inspection. The new convex objective is different from RF auxiliary IA-BCE training; it is not represented as a reproduction of the original learning algorithm. No labels, scopes or thresholds change. Same baseline/FP/drift guards remain; no new GPU job is needed for this diagnostic.','',
'The strict ONNX numerical-export hold remains separate, and no new candidate is promoted to the app. Original models, data, receipts and the four rejected last.pt states are retained.','',
'Next step: complete the cached-feature CPU probes, because they test a more anchored classifier while avoiding repeated frozen-backbone GPU computation.','']
with (HERE/'REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
print(str(HERE/'REPORT.md'))
