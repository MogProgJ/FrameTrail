# Tracking reliability and evaluation (0.11)

This stage adds native scene-boundary handling, confirmation after long gaps, an experimental association repair module, and local identity/event evaluation tooling. The saved-analysis layout, upload/drop workflow, review, saving and CSV controls stay as they are. Both pinned detection models and CPU/GPU execution paths are retained.

## Default behaviour

The player, whole-file analysis, live worker and CLI now share `FrameTracker`, a small composition of the pixel-independent `Tracker` and `SceneBoundary`. A detected visual discontinuity clears active associations, trails and crossing arms. New observations receive fresh monotonically increasing run IDs; accumulated valid crossing counts remain. This prevents IDs and imagined crossings from being carried across a detected cut. Saved appearances therefore split at detected boundaries without changing their presentation or reconstructing older analyses.

The guard samples a bounded 32 × 18 RGB thumbnail, using four samples per cell, and a 16-bin histogram per channel. It requires a mean spatial residual above 0.16 and histogram total-variation distance above 0.18. Removing the average per-channel change suppresses uniform exposure shifts. Frame-size changes also clear continuity. Those are conservative heuristic thresholds, not a learned scene detector or guaranteed cut coverage. Similar-colour cuts, dark edits, fades, camera movement and flashes remain limitations. No model service or full-frame history is added.

A retained identity now becomes tentative again after the existing long-gap threshold: over 250 ms, or over three sequence steps without timestamps. It must accumulate three new observations to confirm. Expiry remains 750 ms / 15 steps. This changes confidence in continuity, not the detector's class labels.

The main player's confirmed boxes now share their stable ID colour with their trails. Tentative tracks use muted dashed outlines; trail opacity increases toward the newest observation. No additional controls or result panels are added. Saved review retains its existing rendering style and layout.

## Experimental association repair

The GUI **keeps greedy association by default**. The native repair option first computes the existing deterministic greedy matches. Only if fewer than the possible number of observations/tracks match does it consult a bounded rectangular Hungarian solver. It replaces the greedy assignment only when the permitted graph admits strictly more matches. Within that repaired solution it minimizes total candidate cost. Class, motion, overlap and distance gates are unchanged; forbidden pairs remain forbidden. This is a hybrid repair, not unconditional global optimization on every frame and not appearance-based re-identification.

The solver uses observations as rows, tracks as columns and private unmatched columns. Penalties guarantee maximum permitted match count before minimizing cost. It supports the existing limits of 256 selected observations and 512 active tracks. Dense worst-case work remains bounded but can be costly; the 256 × 512 equal-cost stress check took about 73 ms on this laptop. Normal clip rules were much cheaper. The mathematical assignment problem is described in [SciPy's official assignment guide](https://github.com/scipy/scipy/blob/main/doc/source/tutorial/optimize.rst); SciPy is not a product dependency or the implementation used here.

```powershell
.\build\windows-msvc\Release\frametrail.exe inspect recording.mp4 --detect models\yolox_s.onnx --model-type small --backend auto --track --association repair --tracks output\repair-tracks.csv --events output\repair-events.csv
```

`greedy` is the default. `repair` is explicitly experimental because increasing association coverage can preserve the wrong identity in a crowd. New saved runs retain their selected policy in an optional schema-3 column. Previous schema-1/2/3 files are read without migration; missing policy means the historical greedy baseline.

## Acceptance evidence and deployment decision

The controlled competing-candidate replay exposes a greedy failure: four identity changes, four distinct IDs for two objects, and one of two expected crossings. Repair produces zero changes, two IDs and both crossings. Brief occlusion, overlapping/reordered observations and same-position different classes retain their expected IDs/events. The standalone solver is checked against exhaustive optima on 400 seeded small rectangular problems, plus a dense maximum-size case. Synthetic trajectories isolate association/rules; they are not detector or natural-video accuracy results.

Three supplied generated recordings were each processed completely: 240 frames per clip, H.264 1280 × 720 at 24 FPS, YOLOX-S, DirectML 1.24.4 on the GTX 1650 Ti, confidence 0.35, NMS 0.45, people class 0 and a vertical line from (0.5, 0.1) to (0.5, 0.9). Before observing exports, seven selected person identities were labelled at original source sequences 6, 12 and 18: 21 approximate boxes across nine frames. These are sparse, partial annotations in the first shot; they cannot establish full precision, event accuracy, all identity switches or real-camera robustness.

The final default and experimental paths recover all 21 selected targets. Default sampled ID-change counts match 0.10: one in the station, zero in the market and zero in the forest. Experimental repair leaves the station's sampled ID-change count at one, introduces one change in the market where the baseline has zero, and leaves the dark forest at zero. That fails the default-adoption gate. The GUI and shipped CLI default therefore retain greedy association. Broader held-out identity labels are required before promotion; the improved synthetic case is insufficient evidence by itself.

The default scene guard detects four station boundaries at sequences 31, 59, 172 and 202. Adjacent before/after images were manually reviewed: each is an actual cut, and exported IDs never span those boundaries. Some other station transitions and the market/dark edits are missed. No scene recall or universal protection claim is made. Thresholds were not tuned to eliminate the supplied clip's measured ID changes.

Sanitized evidence is in [the measurement summary](benchmarks/2026-10-03-tracking.json). Footage, extracted frames, labels, complete native commands/logs, CSVs and detailed reports remain local in ignored `output/tracking-0.11`. Camera capture was not activated. The final native/desktop suite has 34 checks, including four opt-in GPU checks; the Python scorers have 16 checks. Old saved analyses and unchanged intake/save/export paths remain covered.

## Label and score another recording

Export all decoded-frame tracks/events using one frozen model/backend/rule configuration. Preserve its command, input/model/executable hashes and native log. CLI profile CSV now appends `scene_boundary`, `scene_difference` and `scene_histogram_distance`; the earlier timing columns retain their meaning. A native summary reports the association policy and boundary-reset count.

Write a JSON manifest with original pixel boxes and source frame sequences. Use consistent, shot-local reference IDs. `complete: true` means all selected-class objects in that frame, or all selected-class crossings in the explicitly reviewed event interval, were labelled. Otherwise leave it false. Frame zero seeds the tracker and is not in temporal CSV, so evaluation starts at sequence 1.

```json
{
  "schema": 1, "width": 1280, "height": 720,
  "frames": [{"sequence": 20, "complete": false, "objects": [
    {"object_id": "shot1-person-a", "class_id": 0, "box": [100, 100, 200, 400]}
  ]}],
  "events": {"complete": false, "start_sequence": 1, "end_sequence": 240, "items": [
    {"event_id": "crossing-1", "object_id": "shot1-person-a", "sequence": 20, "direction": "negative_to_positive"}
  ]}
}
```

These boxes and events illustrate the schema; they are not usable reference labels. An event needs a labelled identity box within its source-frame tolerance. Its direction uses the configured endpoint order. Event sequence means the confirming observation, not an interpolated physical time.

```powershell
python -B scripts\evaluate-tracking.py --manifest samples\tracking-labels.json --tracks output\tracks.csv --events output\events.csv --output output\tracking-report-new.json --event-tolerance 2
python -B -m unittest discover -s tests -p "test*evaluation.py"
```

The tool uses maximum-cardinality, one-to-one same-class matching at IoU 0.5. It reports matched/missed reviewed targets, ID changes between labelled matches, IDs shared by multiple reference objects as review hints, and one-to-one event matches by identity/class/direction within the source-frame tolerance. Duplicate hints cannot match an expected event twice. Predictions outside the reviewed event interval do not receive credit. Partial annotations leave false-positive counts null. Sparse ID changes are not HOTA, IDF1 or MOTA; gaps and unlabelled frames can conceal mistakes. CSV hashes identify files but do not prove source/model provenance. Reports refuse existing output filenames. Python remains optional developer tooling, outside inference.

Next: obtain genuinely stationary, permissioned footage with complete person/vehicle identities and crossings, and evaluate longer camera movement/occlusion cases. Improve or reject experimental repair based on those held-out results. Training, cloud services and agents remain behind their existing gates.
