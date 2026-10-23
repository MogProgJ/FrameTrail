# FrameTrail experimental RF local preview

This is the trained RF candidate from KIT job 7758628, selected at update 1200.
Training changed the decoder and detection/classification heads; the backbone was frozen.
The app executes an FP32 ONNX export of those learned weights. It does not load the original pretrained detector in their place.

## Start and use

Open `out/FrameTrail-RF7758628-experimental/Run-RF-Experimental.cmd`.
The launcher selects **RF-DETR · trained 7758628 · experimental** and CPU.
Open local media, or choose Video analysis, choose a video, Analyse, review, then optionally Save analysis / Export CSV.
The model is also available in the model selector and in Analysis settings.
Launching the executable without the RF flag retains the existing normal default.

## What this candidate can and cannot show

The checkpoint has learned, but its evaluation failed the adoption gates because false positives increased substantially.
The integration deliberately exposes the actual candidate output, including those errors.
The training set contained positive examples for 115 categories; the 615-label registry is not evidence of accuracy on 615 categories.
The later calibration audit is separate annotation evidence. It has **not** been trained into these weights.
Opening media does inference only; it does not train or update the model.
This build does not change production model selection or launch another training/acquisition job.

CPU inference is verified. Six probes took roughly 305–402 ms per image for inference alone on this computer; this is not an end-to-end video-speed guarantee.
The GPU choice falls back to CPU for this RF profile because DirectML parity has not been verified.
Export parity used confidence 0.35, class-wise NMS 0.45 and maximum 100 detections. Other confidence settings remain exploratory.

## Saved work

Existing source changes, installed app folders, annotations and saved analyses were preserved.
Original changed source files are backed up under `C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3\rf-local-7758628\originals`.
Use the new build to reopen analyses created with the RF profile; older builds do not recognize that profile.
The new build continues to read existing analyses. Merely opening an analysis does not rewrite it.

## Identity and verification

- Source checkpoint SHA-256: `1b72fc6474780a6805e919db5b1393d7e78b95209debafafce98c929c633f0d7`.
- Export SHA-256: `5a5ea0754c11cb664a1b5962efb40071173a6b837e8cbcc490617c4cd227a1f5`.
- Native preprocessing matched the reference tensors exactly on six probes.
- Decoded detections matched within fixed IoU/confidence/geometry tolerances.
- Adapter, wrong-model rejection, cancellation and CPU/GPU guard checks passed.
- RF preview, video analysis, save, CSV and reopening passed; screenshots were inspected.
- Existing detection, saved-run, CLI and desktop regression checks passed.

Evidence: `C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3\rf-local-7758628`. Failed model-quality gates remain documented in `C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3\rf-scale-evaluation-7758628-v1\RESULTS.md`.
