# Equipment and setup plan

## Equipment

No hardware purchase is required to begin the offline prototype. The inspected machine has an i7-10750H CPU, approximately 15.8 GiB RAM, and a GTX 1650 Ti. The native media inspector and desktop preview have been built and checked; representative processing speed and model feasibility still need measurement.

| Item | Initial requirement | Later use |
| --- | --- | --- |
| Windows computer | Existing machine; inspect CPU, RAM, GPU, architecture, and free space | Establish deployment baseline |
| Local images and recordings | Short, permissioned samples with known expected results | Wider accuracy evaluation |
| Dedicated GPU | Optional; CPU is the first execution baseline | Improve throughput if supported and measured |
| Webcam | Not needed for offline milestones | First live-input source |
| Network camera | Not needed initially | Network and reconnection testing |
| Storage | Space for dependencies, models, samples, and temporary outputs | Recording capacity if live replay is added |

RAM, storage, and GPU requirements are not established yet. We will document measured peak memory and model requirements before specifying minimum hardware. Model input size, original video resolution, codec, and number of sources all influence resource use.

## Proposed tools and dependencies

The project now uses C++20/MSVC, CMake, pinned FFmpeg, Qt 6.11.3 Widgets, ONNX Runtime 1.30.0 CPU, and YOLOX-Nano. Qt and inference SDKs are local dependencies. Preprocessing is native C++, so OpenCV is not currently needed; SQLite remains planned. See the [development guide](DEVELOPMENT.md) and [detection guide](DETECTION.md) for setup and model details.

| Tool/dependency | Role | Official reference |
| --- | --- | --- |
| C++20 compiler | Compile application code; MSVC is the proposed Windows baseline | [MSVC support](https://learn.microsoft.com/en-us/cpp/overview/visual-cpp-language-conformance) |
| CMake | Define and generate builds | [CMake documentation](https://cmake.org/documentation/) |
| Qt | Desktop controls, event handling, and rendering | [Qt documentation](https://doc.qt.io/) |
| FFmpeg | Native decoding and pixel conversion | [FFmpeg documentation](https://ffmpeg.org/documentation.html) |
| OpenCV | Image loading and selected image/geometry operations | [OpenCV documentation](https://docs.opencv.org/) |
| ONNX Runtime | Execute an existing object-detection model through native APIs | [C++ getting started](https://onnxruntime.ai/docs/get-started/with-cpp.html) |
| SQLite | Local run and event storage | [SQLite documentation](https://sqlite.org/docs.html) |

The ONNX Runtime C++ interface wraps its C API. Its execution-provider system offers hardware backends, but compatibility is backend-specific. Choose and verify a backend only after inspecting the machine. [C++ API introduction](https://onnxruntime.ai/docs/get-started/with-cpp.html), [execution providers](https://onnxruntime.ai/docs/execution-providers/).

## Model selection gate

The initial selected model is the official YOLOX-Nano 0.1.1rc0 ONNX export, acquired separately with a pinned checksum. The adapter's tensor contract and a reference-image check are documented in [DETECTION.md](DETECTION.md). Future model changes should record:

1. Original model and weight source, version, checksum, and redistribution license.
2. Input size, tensor layout, colour order, scaling, padding, and normalisation.
3. Output format, label mapping, bounding-box convention, and whether suppression is inside the model.
4. Runtime/opset compatibility and CPU execution success.
5. Accuracy on the selected clips, inference time, and peak memory.

An ONNX file format does not grant redistribution rights. Keep model metadata separate from runtime/library licensing. The first application uses pretrained inference rather than training.

## Dependency and distribution decisions

Project license, versions for remaining dependencies, packaging method, and model distribution remain open. Review the chosen Qt modules and the actual FFmpeg build configuration before distributing an executable. FFmpeg licensing depends on enabled components. [FFmpeg licensing](https://ffmpeg.org/legal.html).

Record library notices and model/footage permissions with the selected artifacts. Useful starting references are [Qt licensing](https://www.qt.io/licensing/), [OpenCV licensing](https://opencv.org/license/), and [SQLite copyright](https://sqlite.org/copyright.html). These links are references, not a completed licensing review.

## Sample footage

Use short clips with a stationary camera: a single crossing, opposite directions, repeated crossing, no crossing, partial obstruction, and multiple nearby objects. Include still images and a clip with variable presentation timing. Manually label expected events before assessing the application.

Store local footage, model weights, analysis databases, and generated thumbnails outside tracked documentation. The initial `.gitignore` provides suggested local folders (`samples/`, `models/`, and `output/`) for this purpose. Do not commit large artifacts by default.
