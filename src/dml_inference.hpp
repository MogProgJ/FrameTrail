#pragma once
#include "frametrail/detector.hpp"

namespace frametrail {
// Native GPU adapter: private API, owned tensors only, no UI or tracking dependencies.
class DmlInference {
public:
    DmlInference(const DetectorOptions& options);
    ~DmlInference();
    DmlInference(const DmlInference&) = delete;
    std::vector<float> run(std::span<float> tensor, std::stop_token stop);
    const ExecutionInfo& info() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
