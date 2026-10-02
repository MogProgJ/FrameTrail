# Glossary

| Term | Meaning in FrameTrail |
| --- | --- |
| Frame | One image from a video or camera stream |
| Decode | Convert compressed media into pixels the application can process |
| Pixel format | How colour information is represented in memory |
| Stride | Number of bytes between the starts of adjacent image rows; it can include padding |
| Tensor | A multidimensional array used as a model input or output |
| Inference | Running an existing model to obtain predictions |
| Detection | A predicted object class, confidence, and location in one frame |
| Bounding box | Rectangle describing an object's predicted location |
| Confidence | A model score used to filter predictions; it is not automatically a calibrated probability |
| Non-maximum suppression | A method for removing overlapping duplicate detections |
| Tracking | Associating observations across frames to maintain an object's temporary identity |
| Identity switch | A tracker incorrectly assigning or changing an object's identity |
| Event | A rule-triggered observation, such as a tracked object crossing a line |
| Hysteresis / deadband | A tolerance region or state rule that reduces flickering decisions near a boundary |
| Presentation timestamp | Time at which a decoded frame belongs in the media timeline |
| Monotonic clock | A clock suited to elapsed-time measurements because wall-clock adjustments do not move it backwards |
| FPS | Frames per second; processing and display rates can differ |
| Throughput | Amount of work completed per unit time |
| Latency | Delay between a defined input point and its corresponding result |
| Bounded queue | A buffer with a maximum capacity |
| Backpressure | Slowing an upstream producer when a downstream stage cannot keep up |
| RAII | C++ resource management where an owning object's lifetime controls resource release |
| Execution provider | ONNX Runtime backend that runs supported model operations on particular hardware |
| ONNX | Model exchange format; it does not specify a model's distribution license |
| Run | One analysis job with a fixed source and configuration snapshot |
| Ground truth | Manually checked expected results used to evaluate the application |

## One example through the pipeline

A decoder produces frame 420 with its source timestamp. Preprocessing creates the model's input tensor and remembers how resizing changed coordinates. Inference returns a person detection. The tracker associates it with object 12. The object's anchor moves across the configured line, so the event engine emits a crossing event. Storage saves the event and the interface links it to that moment in the recording.

If the input is a single image, processing ends with detections. No movement or crossing is inferred from that image alone.
