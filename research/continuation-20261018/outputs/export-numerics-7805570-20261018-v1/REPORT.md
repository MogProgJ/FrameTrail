# Export numerical investigation

The original export stays held. On 202 unique images across six references, the ONNX model preserves decoded counts/classes and all measured scoped scores. Three confidence comparisons exceed the original 0.002 tolerance; the maximum difference is 0.004229903. Three of six raw-array probes also fail. Metrics agreement does not waive the numerical failures.

The fixed nine-probe diagnostic found decoded PyTorch results unchanged by the stock export preparation. ORT optimization settings and selected fusion changes moved individual numerical failures without producing a uniform fix. A regular-forward legacy export hit unsupported antialiased bicubic interpolation. Caching the fixed input positional table enabled a regular export, but the three decoded confidence cases persisted. A newer Dynamo/opset-18 export also preserved those failures.

The newer export helpers were installed only into this output's isolated exporter-overlay; the pinned training environment was not upgraded. Installation provenance is recorded in exporter-overlay-install.json. Alternate ONNX files are diagnostic outputs and are not packaged as app defaults.

No model weights, thresholds or original gate results were changed. The explicit native preview carries the numerical limitation; production_adoption remains false. The training proposal is a separate accuracy experiment and cannot resolve this engineering hold.

Inspect DIAGNOSIS.json, FUSION_DIAGNOSIS.json, REGULAR_POSITIONS_DIAGNOSIS.json, DYNAMO_POSITIONS_DIAGNOSIS.json and SEMANTIC_PARITY.json for reproducible observations.

Next step: retain this numerical hold during the proposed billboard trial, so any model gain remains separate from runtime qualification.
