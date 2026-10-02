# Current status

Updated: 2 October 2026.

## What exists

- Documentation for the product and its initial workflow.
- A text interface sketch and Mermaid architecture diagram.
- Proposed module responsibilities and data contracts.
- Equipment/dependency planning, milestones, and a glossary.
- Git ignore and text-formatting configuration.

There is no source code, build definition, executable, selected model, or installed project dependency. No benchmark or accuracy result has been produced.

## Repository publication

Working repository name: **FrameTrail**. GitHub owner: **MogProgJ**.

Repository: [MogProgJ/FrameTrail](https://github.com/MogProgJ/FrameTrail). Created as a private repository on 2 October 2026.

The documentation is prepared locally inside the currently writable workspace. This directory is an independent project, even though its temporary location is below the MiniERP workspace.

GitHub CLI authentication was verified outside the sandbox for the intended account, `MogProgj`. The connector is authenticated as another user and was not used to create this project.

## Decisions already made

- Recorded files and images before live input.
- Stationary-camera person/vehicle crossing events as the first video use case.
- One source and one model for the initial release.
- CPU baseline before deciding on acceleration.
- C++ application with native C API integration; custom C modules only for a justified need.
- Robotics remains a separate shelved idea.

## Decisions still open

- Confirm or rename FrameTrail.
- Initial repository visibility is private because no publication preference was specified; it can be changed later.
- Exact compiler/dependency versions and acquisition method.
- Detection model, weights license, and sample sources.
- Hardware-dependent targets and initial supported file formats.
- Tracker choice and rule parameters.
- Project license and distribution model.

## Immediate next work

Inspect hardware, choose the model and sample footage, and pin the implementation environment before beginning the media foundation milestone.

No application coding is authorized by this documentation milestone alone; the next implementation step should follow the user's direction.
