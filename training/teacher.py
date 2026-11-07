"""YOLOX-S as a labelling teacher for round 3 (see pseudo_labels.py).

The preprocessing and decoding are a port of the app's own detector (src/detector.cpp, `yolox::preprocess` and
`yolox::postprocess`): BGR values in 0..255, half-pixel bilinear resize rounded to whole numbers, top-left letterbox
padded with 114, and the same grid decoding, class-wise NMS and 100-box limit. `tests/test_training_pipeline.py`
checks the decoding on a synthetic output; comparing a real image with `frametrail inspect --model-type small`
was done once by hand (see AGENTS.md).

The model is the publisher's YOLOX-S 0.1.1rc0 export named in dependencies/yolox-small.json (80 COCO classes).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SIZE = 640
STRIDES = (8, 16, 32)
ATTRIBUTES = 85
MAX_DETECTIONS = 100
PAD = 114.0
VOCABULARY = Path(__file__).resolve().parents[1] / 'dependencies' / 'recognition-vocabulary.json'
MODEL_SHA256 = 'c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063'
MODEL_URL = 'https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx'


def coco_names() -> list[str]:
    """The 80 COCO class names, in the model's output order (the first 80 entries of the app's vocabulary)."""
    return json.loads(VOCABULARY.read_text(encoding='utf-8'))['classes'][:80]


def candidate_count(size: int = SIZE) -> int:
    return sum((size // stride) ** 2 for stride in STRIDES)


def grid(size: int = SIZE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Column, row and stride of every candidate, in the model's output order (stride 8 first, row by row)."""
    columns, rows, strides = [], [], []
    for stride in STRIDES:
        cells = size // stride
        y, x = np.divmod(np.arange(cells * cells), cells)
        columns.append(x)
        rows.append(y)
        strides.append(np.full(cells * cells, stride))
    return np.concatenate(columns), np.concatenate(rows), np.concatenate(strides)


def preprocess(rgb: np.ndarray, size: int = SIZE) -> tuple[np.ndarray, float]:
    """RGB uint8 image [H, W, 3] -> (float32 tensor [1, 3, size, size] in BGR 0..255, resize ratio)."""
    height, width = rgb.shape[:2]
    ratio = min(size / width, size / height)
    new_width, new_height = max(1, int(width * ratio)), max(1, int(height * ratio))
    source_y = np.clip((np.arange(new_height) + 0.5) * height / new_height - 0.5, 0, height - 1)
    source_x = np.clip((np.arange(new_width) + 0.5) * width / new_width - 0.5, 0, width - 1)
    y0, x0 = source_y.astype(int), source_x.astype(int)
    y1, x1 = np.minimum(y0 + 1, height - 1), np.minimum(x0 + 1, width - 1)
    fy, fx = (source_y - y0)[:, None, None], (source_x - x0)[None, :, None]
    pixels = rgb.astype(np.float32)
    top = pixels[y0][:, x0] * (1 - fx) + pixels[y0][:, x1] * fx
    bottom = pixels[y1][:, x0] * (1 - fx) + pixels[y1][:, x1] * fx
    resized = np.floor(top * (1 - fy) + bottom * fy + 0.5)            # std::round for non-negative values
    tensor = np.full((1, 3, size, size), PAD, dtype=np.float32)
    tensor[0, :, :new_height, :new_width] = resized[:, :, ::-1].transpose(2, 0, 1)   # RGB -> BGR, planar
    return tensor, ratio


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU of one box against many; boxes are [x0, y0, x1, y1]."""
    width = np.maximum(0, np.minimum(a[2], b[:, 2]) - np.maximum(a[0], b[:, 0]))
    height = np.maximum(0, np.minimum(a[3], b[:, 3]) - np.maximum(a[1], b[:, 1]))
    inside = width * height
    return inside / ((a[2] - a[0]) * (a[3] - a[1]) + (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]) - inside)


def decode(output: np.ndarray, ratio: float, width: int, height: int, confidence: float,
           nms_iou: float = 0.45, size: int = SIZE) -> list[tuple[int, float, tuple[float, float, float, float]]]:
    """Raw model output [8400, 85] -> [(class index, score, (x0, y0, x1, y1))] in original pixels, best first."""
    if output.shape != (candidate_count(size), ATTRIBUTES):
        raise ValueError(f'unexpected YOLOX output {output.shape}')
    objectness, classes = output[:, 4], output[:, 5:]
    best = classes.argmax(axis=1)
    best_probability = classes[np.arange(len(best)), best]
    score = objectness * best_probability
    valid = (np.isfinite(output).all(axis=1) & (objectness >= 0) & (objectness <= 1) &
             (best_probability >= 0) & (best_probability <= 1) & (score >= confidence))
    columns, rows, strides = grid(size)
    keep = np.flatnonzero(valid)
    keep = keep[np.argsort(-score[keep], kind='stable')]
    if not len(keep):
        return []
    cx = (output[keep, 0] + columns[keep]) * strides[keep] / ratio
    cy = (output[keep, 1] + rows[keep]) * strides[keep] / ratio
    w = np.exp(output[keep, 2].astype(np.float64)) * strides[keep] / ratio
    h = np.exp(output[keep, 3].astype(np.float64)) * strides[keep] / ratio
    boxes = np.stack([np.clip(cx - w / 2, 0, width), np.clip(cy - h / 2, 0, height),
                      np.clip(cx + w / 2, 0, width), np.clip(cy + h / 2, 0, height)], axis=1)
    finite = np.isfinite(boxes).all(axis=1) & (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    boxes, kept_index = boxes[finite], keep[finite]
    kept: list[int] = []
    for i in range(len(boxes)):
        same = [k for k in kept if best[kept_index[k]] == best[kept_index[i]]]
        if not same or iou(boxes[i], boxes[same]).max() <= nms_iou:
            kept.append(i)
            if len(kept) == MAX_DETECTIONS:
                break
    return [(int(best[kept_index[i]]), float(score[kept_index[i]]), tuple(float(v) for v in boxes[i])) for i in kept]


class YoloxTeacher:
    """Runs the YOLOX-S ONNX model on image files (CPU, or CUDA/DirectML when onnxruntime offers it)."""

    def __init__(self, model: Path, threads: int = 4, providers: list[str] | None = None):
        import onnxruntime
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        self.session = onnxruntime.InferenceSession(str(model), options,
                                                    providers=providers or ['CPUExecutionProvider'])
        self.input = self.session.get_inputs()[0].name
        self.names = coco_names()

    def detect(self, path: Path, confidence: float = 0.3) -> list[tuple[str, float, tuple[float, float, float, float]]]:
        from PIL import Image
        with Image.open(path) as image:
            rgb = np.asarray(image.convert('RGB'))
        height, width = rgb.shape[:2]
        tensor, ratio = preprocess(rgb)
        output = self.session.run(None, {self.input: tensor})[0][0]
        return [(self.names[c], s, box) for c, s, box in decode(output, ratio, width, height, confidence)]
