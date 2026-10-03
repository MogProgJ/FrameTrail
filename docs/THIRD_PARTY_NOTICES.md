# Third-party artifact inventory

The package preserves selected upstream license texts and the dependency manifests.
These identify artifacts; this inventory is not a completed public-distribution review.

| Component | Artifact / upstream | Included information |
|---|---|---|
| Qt | 6.11.3 qtbase, SDK revision `5a1194b2d368e2d72c230205c464b04a2f23eccd` | LGPL-3.0 and GPL-3.0 texts; original SDK SBOM with component copyrights and license expressions |
| FFmpeg | BtbN LGPL shared 8.1 artifact pinned in `windows-ffmpeg.json` | Original LICENSE.txt and artifact URL/checksum |
| ONNX Runtime | CPU 1.30.0 | Original MIT LICENSE and ThirdPartyNotices.txt |
| YOLOX-Nano / YOLOX-S | 0.1.1rc0 ONNX export | Apache-2.0 text from reference commit `6ddff4824372906469a7fae2dc3206c7aa4bbaee`; model manifest/hash |
| SQLite | 3.53.4 amalgamation | Public-domain dedication in source header; artifact manifest |
| Microsoft C++ runtime | App-local x64 Microsoft.VC143.CRT from installed Visual Studio | DLL versions and file hashes in package manifest; governed by Visual Studio redistributable terms |

Qt and FFmpeg remain dynamically linked. The package does not prevent replacement
of their DLLs. The full Qt SDK SBOM also describes components/tools that may not be
shipped; the package manifest is the actual file inventory. The optional upstream
dog demonstration photo is not packaged.

License text provenance:

- [Qt LGPL-3.0](https://raw.githubusercontent.com/qt/qtbase/5a1194b2d368e2d72c230205c464b04a2f23eccd/LICENSES/LGPL-3.0-only.txt)
- [Qt GPL-3.0](https://raw.githubusercontent.com/qt/qtbase/5a1194b2d368e2d72c230205c464b04a2f23eccd/LICENSES/GPL-3.0-only.txt)
- [YOLOX license](https://raw.githubusercontent.com/Megvii-BaseDetection/YOLOX/6ddff4824372906469a7fae2dc3206c7aa4bbaee/LICENSE)

Before sharing binaries publicly, complete the transitive notice/source review
(including bundled FFmpeg codecs and Qt third-party libraries), provide required
corresponding source material, and choose FrameTrail's own license. No claim of
public-release licensing readiness is made by this private preview.
