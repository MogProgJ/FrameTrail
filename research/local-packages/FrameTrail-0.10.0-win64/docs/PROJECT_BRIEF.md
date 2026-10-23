# Project brief and first interface sketch

## The problem

Reviewing a long recording manually is slow. Someone who needs to count entrances or find when vehicles entered an area should be able to review a short list of timestamped events instead.

FrameTrail will turn visual observations into explicit events that a user can inspect. Its first audience is someone analysing footage from a stationary camera, such as an entrance or parking area.

## First product outcome

Open a recording, draw a line, analyse it, and receive direction-aware crossing events with timestamps. Every event should link back to the source footage. The same application will detect objects in still images without applying temporal rules.

The application recognises selected object categories and evaluates configured rules. It does not provide general understanding of every activity in a scene.

## Proposed screen

This is a layout sketch, not a screenshot of an implemented application.

```text
+-----------------------------------------------------------------------+
| FrameTrail       Open image/video       Analyse        Cancel         |
+----------------------+--------------------------------+---------------+
| Source and rules     | Video / image preview          | Events        |
|                      |                                |               |
| entrance.mp4         |   [Person #12]                 | 00:00:18.420  |
| People [x]           |        +----+                  | Person crossed|
| Vehicles [ ]         |        |    |                  | A -> B        |
|                      |        +----+                  | [thumbnail]   |
| Confidence: 0.50*    | -------- counting line ------- |               |
| Draw counting line   |                                | 00:00:25.080  |
| Direction: A -> B     |                                | Person crossed|
|                      |                                | A -> B        |
+----------------------+--------------------------------+---------------+
| Playback: [play]  00:00:18 / 00:02:00   ----|----*-------*---------      |
| Processing: 12 fps*   Processing latency: 84 ms*   Export CSV          |
+-----------------------------------------------------------------------+
```

Values marked with an asterisk are illustrative, not benchmarks or settled defaults. Image mode hides playback, the timeline, tracking IDs, and crossing rules. Source-relative times are used for recordings; a recording does not necessarily contain a reliable wall-clock capture time.

## User flows

### Image

Open image -> select categories -> analyse -> review boxes and confidence scores -> export detections.

### Recorded video

Open video -> select categories -> draw a line -> analyse -> review events -> seek to an event -> export events.

Analysis can run independently of playback. Seeking the review player must not alter the analysis job or duplicate stored events. A new analysis starts a separate run.

### Later: live camera

Select camera -> configure rules -> start -> monitor current frames and new events -> stop cleanly.

Live event replay requires separately configured recording or retained clips. A live timestamp alone does not guarantee that footage exists to revisit.

## Release boundaries

The initial release supports one local source, one detection model, image detections, a basic video tracker, one counting line, event persistence, and CSV export. Fixed-camera footage is the evaluation baseline.

Region occupancy, webcam input, network cameras, GPU acceleration, and multiple simultaneous sources are later extensions. Audio analysis, facial identification, general behaviour recognition, cloud hosting, and custom model training are outside the initial scope.

## What makes the work substantial

The engineering includes frame ownership, native library integration, coordinate transforms, bounded queues, object association, event reliability, responsive cancellation, storage, and profiling. Loading a model is one component of the product rather than the whole project.
