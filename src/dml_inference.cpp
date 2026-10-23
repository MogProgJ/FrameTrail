#include "dml_inference.hpp"
#include <array>
#include <stdexcept>
#include <algorithm>

#ifdef FRAMETRAIL_DIRECTML
#define NOMINMAX
#include <windows.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <dml_provider_factory.h>

namespace frametrail {
namespace {
template<class T> using Owned = std::unique_ptr<T,void(ORT_API_CALL*)(T*)>;
struct Library {
    HMODULE value{};
    ~Library(){if(value)FreeLibrary(value);}
};
struct Runtime {
    Library library;
    const OrtApi* api{};
    const OrtDmlApi* dml{};
    std::string version;
    Runtime() {
        std::array<wchar_t,32768> executable{};
        const auto length=GetModuleFileNameW(nullptr,executable.data(),DWORD(executable.size()));
        if(!length || length>=executable.size())throw std::runtime_error("Cannot locate the application GPU runtime");
        const auto path=std::filesystem::path(executable.data()).parent_path()/L"backends"/L"directml"/L"onnxruntime.dll";
        library.value=LoadLibraryExW(path.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        if(!library.value)throw std::runtime_error("Optional DirectML runtime unavailable (Windows error "+std::to_string(GetLastError())+")");
        const auto get=reinterpret_cast<const OrtApiBase*(ORT_API_CALL*)()>(GetProcAddress(library.value,"OrtGetApiBase"));
        if(!get)throw std::runtime_error("Invalid DirectML runtime entry point");
        const auto* base=get();version=base->GetVersionString();
        if(version!="1.24.4")throw std::runtime_error("Unexpected isolated DirectML runtime version: "+version);
        // API-24's stable C ABI prefix stays private to this module. Its resources
        // must never be passed to the linked CPU runtime's C++ API.
        api=base->GetApi(24);if(!api)throw std::runtime_error("DirectML runtime C API 24 unavailable");
        check(api->GetExecutionProviderApi("DML",24,reinterpret_cast<const void**>(&dml)));
    }
    void check(OrtStatus* status) const {
        if(!status)return;
        const std::string error=api->GetErrorMessage(status);api->ReleaseStatus(status);
        throw std::runtime_error("DirectML: "+error);
    }
};
std::shared_ptr<Runtime> runtime() {
    // Retain the module until process exit, after all tensors/sessions are released.
    static const auto value=std::make_shared<Runtime>();return value;
}
std::pair<int,std::string> adapter(int requested) {
    Microsoft::WRL::ComPtr<IDXGIFactory1> factory;
    if(FAILED(CreateDXGIFactory1(IID_PPV_ARGS(&factory))))throw std::runtime_error("Cannot enumerate DirectX adapters");
    int selected=-1;SIZE_T memory{};std::string name;
    for(UINT index=0;;++index) {
        Microsoft::WRL::ComPtr<IDXGIAdapter1> device;
        const auto result=factory->EnumAdapters1(index,&device);
        if(result==DXGI_ERROR_NOT_FOUND)break;
        if(FAILED(result))throw std::runtime_error("DirectX adapter enumeration failed");
        DXGI_ADAPTER_DESC1 description{};
        if(FAILED(device->GetDesc1(&description)))continue;
        if(description.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)continue;
        if(requested>=0 && requested!=int(index))continue;
        if(FAILED(D3D12CreateDevice(device.Get(),D3D_FEATURE_LEVEL_11_0,__uuidof(ID3D12Device),nullptr)))continue;
        if(selected<0 || description.DedicatedVideoMemory>memory) {
            selected=int(index);memory=description.DedicatedVideoMemory;
            const auto count=WideCharToMultiByte(CP_UTF8,0,description.Description,-1,nullptr,0,nullptr,nullptr);
            std::string text(std::max(count,1),'\0');
            WideCharToMultiByte(CP_UTF8,0,description.Description,-1,text.data(),int(text.size()),nullptr,nullptr);
            if(!text.empty() && text.back()=='\0')text.pop_back();name=std::move(text);
        }
    }
    if(selected<0)throw std::runtime_error("Requested DirectX 12 hardware adapter is unavailable");
    return {selected,name};
}
}
struct DmlInference::Impl {
    std::shared_ptr<Runtime> owner{runtime()};
    const OrtApi* api{owner->api};
    Owned<OrtEnv> env{nullptr,api->ReleaseEnv};
    Owned<OrtSession> session{nullptr,api->ReleaseSession};
    std::string input_name,output_name;
    int size{};
    DetectorModel variant;
    ExecutionInfo execution;
    void check(OrtStatus* status) const {owner->check(status);}
    void shape(const OrtTensorTypeAndShapeInfo* info,const std::vector<int64_t>& expected) const {
        ONNXTensorElementDataType type{};std::size_t count{};
        check(api->GetTensorElementType(info,&type));check(api->GetDimensionsCount(info,&count));
        std::vector<int64_t> dimensions(count);check(api->GetDimensions(info,dimensions.data(),count));
        if(type!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT || dimensions!=expected)
            throw std::runtime_error("DirectML model tensor contract differs from the selected detector profile");
    }
    Impl(const DetectorOptions& options):size(model_input_size(options.variant)),variant(options.variant) {
        const auto [index,name]=adapter(options.gpu_device);execution={"DirectML",owner->version,name,{}};
        OrtEnv* raw_env{};check(api->CreateEnv(ORT_LOGGING_LEVEL_WARNING,"FrameTrail GPU",&raw_env));env.reset(raw_env);
        check(api->DisableTelemetryEvents(env.get()));
        OrtSessionOptions* raw_options{};check(api->CreateSessionOptions(&raw_options));
        Owned<OrtSessionOptions> settings(raw_options,api->ReleaseSessionOptions);
        check(api->DisableMemPattern(settings.get()));check(api->SetSessionExecutionMode(settings.get(),ORT_SEQUENTIAL));
        check(api->SetSessionGraphOptimizationLevel(settings.get(),ORT_ENABLE_ALL));
        check(api->SetIntraOpNumThreads(settings.get(),4));check(api->SetInterOpNumThreads(settings.get(),1));
        check(owner->dml->SessionOptionsAppendExecutionProvider_DML(settings.get(),index));
        OrtSession* raw_session{};check(api->CreateSession(env.get(),options.model.c_str(),settings.get(),&raw_session));session.reset(raw_session);
        std::size_t inputs{},outputs{};check(api->SessionGetInputCount(session.get(),&inputs));check(api->SessionGetOutputCount(session.get(),&outputs));
        if(inputs!=1 || outputs!=1)throw std::runtime_error("Expected one detector input and output");
        for(bool input:{true,false}) {
            OrtTypeInfo* raw_type{};
            check(input ? api->SessionGetInputTypeInfo(session.get(),0,&raw_type):api->SessionGetOutputTypeInfo(session.get(),0,&raw_type));
            Owned<OrtTypeInfo> type(raw_type,api->ReleaseTypeInfo);const OrtTensorTypeAndShapeInfo* tensor{};
            check(api->CastTypeInfoToTensorInfo(type.get(),&tensor));
            if(!tensor)throw std::runtime_error("detector input/output must be tensors");
            shape(tensor,input ? std::vector<int64_t>{1,3,size,size}:model_output_shape(variant));
        }
        OrtAllocator* allocator{};check(api->GetAllocatorWithDefaultOptions(&allocator));
        if(model_class_count(variant)>80) {
            OrtModelMetadata* raw_metadata{};check(api->SessionGetModelMetadata(session.get(),&raw_metadata));
            Owned<OrtModelMetadata> metadata(raw_metadata,api->ReleaseModelMetadata);
            std::vector<const char*> keys{"frametrail.profile","frametrail.vocabulary"};
            if(variant==DetectorModel::rf_scale7758628) {
                keys.push_back("frametrail.checkpoint_sha256");keys.push_back("frametrail.preprocessing");
            }
            for(const auto* key:keys) {
                char* raw{};check(api->ModelMetadataLookupCustomMetadataMap(metadata.get(),allocator,key,&raw));
                std::string text;
                try{if(raw)text=raw;}catch(...){if(raw)allocator->Free(allocator,raw);throw;}
                if(raw)allocator->Free(allocator,raw);
                const std::string_view field(key);
                const auto expected=field=="frametrail.profile" ? std::string(model_id(variant)):
                    field=="frametrail.vocabulary" ? model_vocabulary(variant):
                    field=="frametrail.checkpoint_sha256" ? std::string(rfdetr::checkpoint_sha256):std::string("rf-rgb512-normalized-v1");
                if(text!=expected)throw std::runtime_error("DirectML recognition profile/vocabulary or RF identity/preprocessing mismatch");
            }
        }
        for(bool input:{true,false}) {
            char* raw_name{};
            check(input ? api->SessionGetInputName(session.get(),0,allocator,&raw_name):api->SessionGetOutputName(session.get(),0,allocator,&raw_name));
            try{(input ? input_name:output_name)=raw_name;}catch(...){allocator->Free(allocator,raw_name);throw;}
            allocator->Free(allocator,raw_name);
        }
    }
    std::vector<float> run(std::span<float> pixels,std::stop_token stop) {
        if(stop.stop_requested())throw std::runtime_error("Detection cancelled");
        if(pixels.size()!=std::size_t(3)*size*size)throw std::invalid_argument("Invalid model input tensor size");
        OrtMemoryInfo* raw_memory{};check(api->CreateCpuMemoryInfo(OrtArenaAllocator,OrtMemTypeDefault,&raw_memory));
        Owned<OrtMemoryInfo> memory(raw_memory,api->ReleaseMemoryInfo);
        const std::array<int64_t,4> dimensions{1,3,size,size};OrtValue* raw_input{};
        check(api->CreateTensorWithDataAsOrtValue(memory.get(),pixels.data(),pixels.size_bytes(),dimensions.data(),dimensions.size(),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&raw_input));
        Owned<OrtValue> input(raw_input,api->ReleaseValue);
        OrtRunOptions* raw_run{};check(api->CreateRunOptions(&raw_run));Owned<OrtRunOptions> options(raw_run,api->ReleaseRunOptions);
        std::stop_callback interrupt(stop,[&]() noexcept {if(auto* status=api->RunOptionsSetTerminate(options.get()))api->ReleaseStatus(status);});
        const char* inputs[]{input_name.c_str()};const char* outputs[]{output_name.c_str()};const OrtValue* tensors[]{input.get()};OrtValue* raw_output{};
        auto* status=api->Run(session.get(),options.get(),inputs,tensors,1,outputs,1,&raw_output);
        Owned<OrtValue> output(raw_output,api->ReleaseValue);check(status);
        if(stop.stop_requested())throw std::runtime_error("Detection cancelled");
        OrtTensorTypeAndShapeInfo* raw_shape{};check(api->GetTensorTypeAndShape(output.get(),&raw_shape));
        Owned<OrtTensorTypeAndShapeInfo> type(raw_shape,api->ReleaseTensorTypeAndShapeInfo);
        shape(type.get(),model_output_shape(variant));std::size_t count{};check(api->GetTensorShapeElementCount(type.get(),&count));
        float* values{};check(api->GetTensorMutableData(output.get(),reinterpret_cast<void**>(&values)));
        return {values,values+count}; // Owned CPU copy; synchronous Run includes transfers.
    }
};
DmlInference::DmlInference(const DetectorOptions& options):impl_(std::make_unique<Impl>(options)){}
DmlInference::~DmlInference()=default;
std::vector<float> DmlInference::run(std::span<float> tensor,std::stop_token stop){return impl_->run(tensor,stop);}
const ExecutionInfo& DmlInference::info() const{return impl_->execution;}
}
#else
namespace frametrail {
struct DmlInference::Impl{};
DmlInference::DmlInference(const DetectorOptions&){throw std::runtime_error("GPU support is not built; run scripts/fetch-gpu.ps1 and rebuild");}
DmlInference::~DmlInference()=default;
std::vector<float> DmlInference::run(std::span<float>,std::stop_token){throw std::logic_error("GPU support is not built");}
const ExecutionInfo& DmlInference::info() const{throw std::logic_error("GPU support is not built");}
}
#endif
