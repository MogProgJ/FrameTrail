cmake_minimum_required(VERSION 3.25)
project(FrameTrail VERSION 0.12.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)
find_package(Threads REQUIRED)
option(FRAMETRAIL_BUILD_GUI "Build the Qt desktop preview" ON)
option(FRAMETRAIL_TEST_GPU "Run opt-in GPU hardware checks" OFF)

# Dependencies are acquired explicitly, never downloaded during configuration.
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/windows-ffmpeg.json" _manifest)
string(JSON _package GET "${_manifest}" archiveRoot)
set(FFMPEG_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_package}" CACHE PATH "FFmpeg SDK root")
if(NOT EXISTS "${FFMPEG_ROOT}/include/libavcodec/avcodec.h")
    message(FATAL_ERROR
        "FFmpeg development SDK is missing at: ${FFMPEG_ROOT}\n"
        "The .deps directory is local and is not included in Git clones.\n"
        "From the FrameTrail folder, run:\n"
        "  powershell -NoProfile -File ./scripts/fetch-dependencies.ps1\n"
        "Then configure again. If using your own SDK, set FFMPEG_ROOT to its root directory.")
endif()

find_path(_ffmpeg_headers libavcodec/avcodec.h HINTS "${FFMPEG_ROOT}/include"
    NO_DEFAULT_PATH NO_CACHE REQUIRED)
foreach(_component avdevice avformat avcodec avutil swscale)
    find_library(_ffmpeg_${_component}_library NAMES ${_component}
        HINTS "${FFMPEG_ROOT}/lib" NO_DEFAULT_PATH NO_CACHE REQUIRED)
    add_library(FFmpeg::${_component} UNKNOWN IMPORTED)
    set_target_properties(FFmpeg::${_component} PROPERTIES
        IMPORTED_LOCATION "${_ffmpeg_${_component}_library}"
        INTERFACE_INCLUDE_DIRECTORIES "${_ffmpeg_headers}")
endforeach()

file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/windows-onnxruntime.json" _ort_manifest)
string(JSON _ort_directory GET "${_ort_manifest}" archiveRoot)
set(ONNXRUNTIME_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_ort_directory}" CACHE PATH "ONNX Runtime CPU SDK")
if(NOT EXISTS "${ONNXRUNTIME_ROOT}/include/onnxruntime_cxx_api.h")
    message(FATAL_ERROR "ONNX Runtime SDK missing. Run scripts/fetch-dependencies.ps1 and configure again.")
endif()
add_library(ONNXRuntime SHARED IMPORTED)
set_target_properties(ONNXRuntime PROPERTIES
    IMPORTED_IMPLIB "${ONNXRUNTIME_ROOT}/lib/onnxruntime.lib"
    IMPORTED_LOCATION "${ONNXRUNTIME_ROOT}/lib/onnxruntime.dll"
    INTERFACE_INCLUDE_DIRECTORIES "${ONNXRUNTIME_ROOT}/include")
set(FRAMETRAIL_MODEL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/models" CACHE PATH "Existing detector model directory")
set(FRAMETRAIL_RF_MODEL "${CMAKE_CURRENT_SOURCE_DIR}/models/rfdetr_scale7758628.onnx" CACHE FILEPATH "Verified experimental RF export")
set(FRAMETRAIL_BALANCED_RF_MODEL "" CACHE FILEPATH "Verified balanced RF export")
set(_detector_model "${FRAMETRAIL_MODEL_ROOT}/yolox_nano.onnx")
set(_detector_small_model "${FRAMETRAIL_MODEL_ROOT}/yolox_s.onnx")
set(_world_s_model "${FRAMETRAIL_MODEL_ROOT}/yolo_world_s.onnx")
set(_openimages_model "${FRAMETRAIL_MODEL_ROOT}/yolo_openimages.onnx")
set(_world_m_model "${FRAMETRAIL_MODEL_ROOT}/yolo_world_m.onnx")
set(_rf_openimages_model "${FRAMETRAIL_MODEL_ROOT}/rfdetr_openimages.onnx")
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/sqlite.json" _sqlite_manifest)
string(JSON _sqlite_directory GET "${_sqlite_manifest}" archiveRoot)
set(SQLITE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_sqlite_directory}" CACHE PATH "SQLite amalgamation root")
if(NOT EXISTS "${SQLITE_ROOT}/sqlite3.c")
    message(FATAL_ERROR "SQLite source missing. Run scripts/fetch-storage.ps1 and configure again.")
endif()
add_library(frametrail_sqlite STATIC "${SQLITE_ROOT}/sqlite3.c")
target_include_directories(frametrail_sqlite PUBLIC "${SQLITE_ROOT}")
target_compile_definitions(frametrail_sqlite PRIVATE SQLITE_THREADSAFE=1 SQLITE_OMIT_LOAD_EXTENSION)
add_library(frametrail_core
    src/live_session.cpp
    src/run_store.cpp
    src/playback_cache.cpp
    src/analysis_job.cpp
    src/tracker.cpp
    src/assignment.cpp
    src/frame_tracker.cpp
    src/detector.cpp
    src/yolo_world.cpp
    src/rfdetr.cpp
    src/dml_inference.cpp
    src/media_reader.cpp
    src/frame_export.cpp
    src/preview_session.cpp)
target_include_directories(frametrail_core PUBLIC include)
target_link_libraries(frametrail_core PRIVATE
    FFmpeg::avdevice FFmpeg::avformat FFmpeg::avcodec FFmpeg::avutil FFmpeg::swscale Threads::Threads ONNXRuntime frametrail_sqlite)
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/windows-directml.json" _dml_manifest)
string(JSON _dml_directory GET "${_dml_manifest}" directory)
set(FRAMETRAIL_DIRECTML_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_dml_directory}" CACHE PATH "Optional DirectML runtime")
option(FRAMETRAIL_ENABLE_DIRECTML "Enable optional native GPU support when acquired" ON)
if(WIN32 AND FRAMETRAIL_ENABLE_DIRECTML AND EXISTS "${FRAMETRAIL_DIRECTML_ROOT}/include/dml_provider_factory.h")
    target_compile_definitions(frametrail_core PRIVATE FRAMETRAIL_DIRECTML)
    target_include_directories(frametrail_core PRIVATE "${FRAMETRAIL_DIRECTML_ROOT}/include")
    target_link_libraries(frametrail_core PRIVATE dxgi d3d12)
    set(_directml_enabled TRUE)
endif()
set(FRAMETRAIL_DIRECTML_BUILT "${_directml_enabled}" CACHE INTERNAL "DirectML compiled into current build" FORCE)
if(MSVC)
    target_compile_options(frametrail_core PRIVATE /W4 /permissive- /utf-8)
else()
    target_compile_options(frametrail_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

function(frametrail_runtime target)
    if(WIN32)
        file(GLOB _runtime_dlls "${FFMPEG_ROOT}/bin/*.dll")
        if(NOT _runtime_dlls)
            message(FATAL_ERROR "FFmpeg runtime DLLs missing. Run scripts/fetch-dependencies.ps1.")
        endif()
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                ${_runtime_dlls} "$<TARGET_FILE_DIR:${target}>"
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:ONNXRuntime>" "$<TARGET_FILE_DIR:${target}>"
            VERBATIM)
        if(_directml_enabled)
            add_custom_command(TARGET ${target} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target}>/backends/directml"
                COMMAND ${CMAKE_COMMAND} -E copy_directory "${FRAMETRAIL_DIRECTML_ROOT}/bin" "$<TARGET_FILE_DIR:${target}>/backends/directml"
                VERBATIM)
        endif()
        foreach(_model IN ITEMS "${_detector_model}" "${_detector_small_model}" "${_world_s_model}" "${_world_m_model}" "${_openimages_model}" "${FRAMETRAIL_RF_MODEL}" "${FRAMETRAIL_BALANCED_RF_MODEL}" "${_rf_openimages_model}")
            if(EXISTS "${_model}")
                add_custom_command(TARGET ${target} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target}>/models"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_model}" "$<TARGET_FILE_DIR:${target}>/models/"
                VERBATIM)
            endif()
        endforeach()
    endif()
endfunction()

add_executable(frametrail apps/cli/main.cpp)
target_link_libraries(frametrail PRIVATE frametrail_core)
if(MSVC)
    target_compile_options(frametrail PRIVATE /W4 /permissive- /utf-8)
endif()
frametrail_runtime(frametrail)

if(FRAMETRAIL_BUILD_GUI)
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/windows-qt.json" _qt_manifest)
    string(JSON _qt_directory GET "${_qt_manifest}" directory)
    set(FRAMETRAIL_QT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_qt_directory}" CACHE PATH "Qt SDK root")
    if(NOT EXISTS "${FRAMETRAIL_QT_ROOT}/lib/cmake/Qt6/Qt6Config.cmake")
        message(FATAL_ERROR "Qt SDK missing. Run scripts/fetch-dependencies.ps1, or configure with -DFRAMETRAIL_BUILD_GUI=OFF for CLI-only builds.")
    endif()
    list(PREPEND CMAKE_PREFIX_PATH "${FRAMETRAIL_QT_ROOT}")
    find_package(Qt6 6.11 REQUIRED COMPONENTS Widgets)
    function(frametrail_qt_runtime target)
        frametrail_runtime(${target})
        if(WIN32)
            set(_plugin_suffix "$<$<CONFIG:Debug>:d>")
            add_custom_command(TARGET ${target} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "$<TARGET_FILE:Qt6::Core>" "$<TARGET_FILE:Qt6::Gui>" "$<TARGET_FILE:Qt6::Widgets>"
                    "$<TARGET_FILE_DIR:${target}>"
                COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target}>/platforms"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    "${FRAMETRAIL_QT_ROOT}/plugins/platforms/qwindows${_plugin_suffix}.dll"
                    "${FRAMETRAIL_QT_ROOT}/plugins/platforms/qoffscreen${_plugin_suffix}.dll"
                    "$<TARGET_FILE_DIR:${target}>/platforms"
                VERBATIM)
        endif()
    endfunction()
    add_library(frametrail_preview_ui apps/desktop/studio_assets.qrc apps/desktop/guide_workspace.cpp apps/desktop/home_workspace.cpp apps/desktop/appearance_timeline.cpp apps/desktop/model_comparison.cpp apps/desktop/workspace_chrome.cpp apps/desktop/playback_workspace.cpp apps/desktop/cached_playback_window.cpp apps/desktop/preview_layout.ui apps/desktop/preview_window.cpp apps/desktop/saved_run_window.cpp apps/desktop/live_window.cpp)
    set_target_properties(frametrail_preview_ui PROPERTIES AUTOUIC ON AUTORCC ON)
    target_include_directories(frametrail_preview_ui PUBLIC apps/desktop)
    target_link_libraries(frametrail_preview_ui PUBLIC frametrail_core Qt6::Widgets)
    if(MSVC)
        target_compile_options(frametrail_preview_ui PRIVATE /W4 /permissive- /utf-8)
    endif()
    add_executable(frametrail-desktop WIN32 apps/desktop/main.cpp)
    if(WIN32)
        target_sources(frametrail-desktop PRIVATE apps/desktop/frametrail.rc)
    endif()
    target_link_libraries(frametrail-desktop PRIVATE frametrail_preview_ui)
    frametrail_qt_runtime(frametrail-desktop)
endif()

if(BUILD_TESTING)
    add_executable(frametrail_backend_tests tests/backend_tests.cpp)
    target_link_libraries(frametrail_backend_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_backend_tests)
    add_test(NAME backend_contract COMMAND frametrail_backend_tests contract "${CMAKE_CURRENT_BINARY_DIR}/fixtures/variable.mkv" "${_detector_model}" nano)
    set_tests_properties(backend_contract PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    if(FRAMETRAIL_TEST_GPU)
        if(NOT _directml_enabled)
            message(FATAL_ERROR "GPU checks require the optional runtime. Run scripts/fetch-gpu.ps1.")
        endif()
        foreach(_gpu_model IN ITEMS nano small)
            if(_gpu_model STREQUAL "nano")
                set(_gpu_path "${_detector_model}")
            else()
                set(_gpu_path "${_detector_small_model}")
            endif()
            add_test(NAME gpu_${_gpu_model}_agreement COMMAND frametrail_backend_tests gpu "${CMAKE_CURRENT_SOURCE_DIR}/.deps/detection-samples/dog.jpg" "${_gpu_path}" "${_gpu_model}")
            set_tests_properties(gpu_${_gpu_model}_agreement PROPERTIES TIMEOUT 45 LABELS gpu)
        endforeach()
        add_test(NAME gpu_saved_analysis COMMAND frametrail_backend_tests saved "${CMAKE_CURRENT_BINARY_DIR}/fixtures/review.mkv" "${_detector_model}" nano "${CMAKE_CURRENT_BINARY_DIR}/fixtures")
        set_tests_properties(gpu_saved_analysis PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 45 LABELS gpu)
    endif()
    add_executable(frametrail_live_tests tests/live_tests.cpp)
    target_link_libraries(frametrail_live_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_live_tests)
    add_test(NAME live_lifecycle COMMAND frametrail_live_tests)
    set_tests_properties(live_lifecycle PROPERTIES TIMEOUT 20)
    add_executable(frametrail_tracking_tests tests/tracking_tests.cpp)
    target_link_libraries(frametrail_tracking_tests PRIVATE frametrail_core)
    if(MSVC)
        target_compile_options(frametrail_tracking_tests PRIVATE /W4 /permissive- /utf-8)
    endif()
    frametrail_runtime(frametrail_tracking_tests)
    add_test(NAME tracking_contract COMMAND frametrail_tracking_tests)
    add_executable(frametrail_tracking_regression tests/tracking_regression.cpp)
    target_link_libraries(frametrail_tracking_regression PRIVATE frametrail_core)
    frametrail_runtime(frametrail_tracking_regression)
    add_test(NAME tracking_regression COMMAND frametrail_tracking_regression)
    add_executable(frametrail_association_tests tests/association_tests.cpp src/assignment.cpp)
    target_include_directories(frametrail_association_tests PRIVATE src)
    add_test(NAME global_assignment_contract COMMAND frametrail_association_tests)
    add_executable(frametrail_frame_tracker_tests tests/frame_tracker_tests.cpp)
    target_link_libraries(frametrail_frame_tracker_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_frame_tracker_tests)
    add_test(NAME scene_tracking_contract COMMAND frametrail_frame_tracker_tests)
    add_executable(frametrail_detection_tests tests/detection_tests.cpp)
    target_link_libraries(frametrail_detection_tests PRIVATE frametrail_core)
    if(WIN32)
        target_link_libraries(frametrail_detection_tests PRIVATE Psapi)
    endif()
    frametrail_runtime(frametrail_detection_tests)
    add_test(NAME detection_contract COMMAND frametrail_detection_tests)
    set(_detection_sample "${CMAKE_CURRENT_SOURCE_DIR}/.deps/detection-samples/dog.jpg")
    add_executable(frametrail_media_tests tests/media_tests.cpp)
    target_link_libraries(frametrail_media_tests PRIVATE frametrail_core)
    if(MSVC)
        target_compile_options(frametrail_media_tests PRIVATE /W4 /permissive- /utf-8)
    endif()
    frametrail_runtime(frametrail_media_tests)
    find_program(_ffmpeg_executable ffmpeg HINTS "${FFMPEG_ROOT}/bin"
        NO_DEFAULT_PATH NO_CACHE REQUIRED)
    set(_fixtures "${CMAKE_CURRENT_BINARY_DIR}/fixtures")
    add_test(NAME generate_media_fixtures COMMAND ${CMAKE_COMMAND}
        "-DFFMPEG=${_ffmpeg_executable}" "-DOUTPUT=${_fixtures}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/generate_fixtures.cmake")
    set_tests_properties(generate_media_fixtures PROPERTIES FIXTURES_SETUP media TIMEOUT 60)
    add_executable(frametrail_run_tests tests/run_tests.cpp)
    target_link_libraries(frametrail_run_tests PRIVATE frametrail_core frametrail_sqlite)
    if(MSVC)
        target_compile_options(frametrail_run_tests PRIVATE /W4 /permissive- /utf-8)
    endif()
    frametrail_runtime(frametrail_run_tests)
    add_test(NAME saved_run_contract COMMAND frametrail_run_tests "${_fixtures}")
    set_tests_properties(saved_run_contract PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    if(EXISTS "${_detector_model}")
        add_test(NAME detection_inference COMMAND frametrail_detection_tests --inference "${_detector_model}" "${_fixtures}")
        set_tests_properties(detection_inference PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
        if(EXISTS "${_detection_sample}")
            add_test(NAME generate_analysis_fixture COMMAND ${CMAKE_COMMAND}
                "-DFFMPEG=${_ffmpeg_executable}" "-DSAMPLE=${_detection_sample}" "-DOUTPUT=${_fixtures}/review.mkv"
                -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/generate_analysis_fixture.cmake")
            set_tests_properties(generate_analysis_fixture PROPERTIES FIXTURES_REQUIRED media FIXTURES_SETUP analysis TIMEOUT 30)
            add_test(NAME saved_analysis_inference COMMAND frametrail_run_tests "${_fixtures}/review.mkv" "${_detector_model}")
            set_tests_properties(saved_analysis_inference PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 60)
            add_test(NAME cli_saved_run COMMAND ${CMAKE_COMMAND}
                "-DCLI=$<TARGET_FILE:frametrail>" "-DMODEL=${_detector_model}" "-DSOURCE=${_fixtures}/review.mkv" "-DFIXTURES=${_fixtures}"
                -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_saved_cli.cmake")
            set_tests_properties(cli_saved_run PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 60)
            add_test(NAME detection_sample COMMAND frametrail_detection_tests --sample "${_detector_model}" "${_detection_sample}")
            set_tests_properties(detection_sample PROPERTIES TIMEOUT 60)
            add_test(NAME cli_detection COMMAND ${CMAKE_COMMAND}
                "-DCLI=$<TARGET_FILE:frametrail>" "-DMODEL=${_detector_model}"
                "-DSAMPLE=${_detection_sample}" "-DFIXTURES=${_fixtures}"
                -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_detection_cli.cmake")
            set_tests_properties(cli_detection PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
            add_test(NAME cli_tracking COMMAND ${CMAKE_COMMAND}
                "-DCLI=$<TARGET_FILE:frametrail>" "-DMODEL=${_detector_model}"
                "-DSAMPLE=${_detection_sample}" "-DFIXTURES=${_fixtures}" "-DFFMPEG=${_ffmpeg_executable}"
                -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_tracking_cli.cmake")
            set_tests_properties(cli_tracking PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
        endif()
    endif()
    if(EXISTS "${_detector_small_model}")
        add_test(NAME cli_model_selection COMMAND ${CMAKE_COMMAND}
            "-DCLI=$<TARGET_FILE:frametrail>" "-DMODEL=${_detector_small_model}" "-DFIXTURES=${_fixtures}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_model_cli.cmake")
        set_tests_properties(cli_model_selection PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
        add_test(NAME detection_small_inference COMMAND frametrail_detection_tests --inference "${_detector_small_model}" "${_fixtures}" small)
        set_tests_properties(detection_small_inference PROPERTIES FIXTURES_REQUIRED media TIMEOUT 90)
        if(EXISTS "${_detection_sample}")
            add_test(NAME detection_small_sample COMMAND frametrail_detection_tests --sample "${_detector_small_model}" "${_detection_sample}" small)
            set_tests_properties(detection_small_sample PROPERTIES TIMEOUT 60)
        endif()
    endif()
    foreach(_expanded_profile world-s world-m openimages)
        if(_expanded_profile STREQUAL "world-s")
            set(_expanded_model "${_world_s_model}")
        elseif(_expanded_profile STREQUAL "world-m")
            set(_expanded_model "${_world_m_model}")
        else()
            set(_expanded_model "${_openimages_model}")
        endif()
        if(EXISTS "${_expanded_model}")
            add_test(NAME detection_${_expanded_profile}_inference COMMAND frametrail_detection_tests --inference "${_expanded_model}" "${_fixtures}" ${_expanded_profile})
            set_tests_properties(detection_${_expanded_profile}_inference PROPERTIES FIXTURES_REQUIRED media TIMEOUT 120)
            if(EXISTS "${_detection_sample}")
                add_test(NAME detection_${_expanded_profile}_sample COMMAND frametrail_detection_tests --sample "${_expanded_model}" "${_detection_sample}" ${_expanded_profile})
                set_tests_properties(detection_${_expanded_profile}_sample PROPERTIES TIMEOUT 120)
                if(FRAMETRAIL_TEST_GPU AND _directml_enabled)
                    add_test(NAME gpu_${_expanded_profile}_parity COMMAND frametrail_backend_tests gpu "${_detection_sample}" "${_expanded_model}" ${_expanded_profile})
                    set_tests_properties(gpu_${_expanded_profile}_parity PROPERTIES TIMEOUT 180 LABELS gpu)
                endif()
            endif()
        endif()
    endforeach()
    if(FRAMETRAIL_TEST_GPU AND EXISTS "${_openimages_model}")
        add_test(NAME gpu_openimages_saved_analysis COMMAND frametrail_backend_tests saved "${_fixtures}/review.mkv" "${_openimages_model}" openimages "${_fixtures}")
        set_tests_properties(gpu_openimages_saved_analysis PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 90 LABELS gpu)
    endif()
    add_test(NAME media_contract COMMAND frametrail_media_tests "${_fixtures}")
    set_tests_properties(media_contract PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_test(NAME cli_help COMMAND frametrail --help)
    if(EXISTS "${_detector_model}")
        add_test(NAME cli_profile COMMAND ${CMAKE_COMMAND}
            "-DCLI=$<TARGET_FILE:frametrail>" "-DFIXTURES=${_fixtures}" "-DMODEL=${_detector_model}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_profile.cmake")
        set_tests_properties(cli_profile PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    endif()
    add_test(NAME cli_exports COMMAND ${CMAKE_COMMAND}
        "-DCLI=$<TARGET_FILE:frametrail>" "-DFIXTURES=${_fixtures}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_cli.cmake")
    set_tests_properties(cli_exports PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_executable(frametrail_preview_tests tests/preview_tests.cpp)
    target_link_libraries(frametrail_preview_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_preview_tests)
    add_test(NAME preview_lifecycle COMMAND frametrail_preview_tests "${_fixtures}")
    set_tests_properties(preview_lifecycle PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_test(NAME preview_reconfiguration COMMAND frametrail_preview_tests "${_fixtures}" --reconfigure)
    set_tests_properties(preview_reconfiguration PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    if(EXISTS "${_detector_model}" AND EXISTS "${_detection_sample}")
        add_test(NAME preview_tracking COMMAND frametrail_preview_tests "${_fixtures}" "${_detector_model}" "${_detection_sample}")
        set_tests_properties(preview_tracking PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
    endif()
    if(FRAMETRAIL_BUILD_GUI)
        find_package(Qt6 REQUIRED COMPONENTS Test)
        if(EXISTS "${_detector_model}" AND EXISTS "${_detection_sample}")
            add_executable(frametrail_saved_desktop_tests tests/saved_desktop_tests.cpp)
            target_link_libraries(frametrail_saved_desktop_tests PRIVATE frametrail_preview_ui Qt6::Test)
            frametrail_qt_runtime(frametrail_saved_desktop_tests)
            if(MSVC)
                target_compile_options(frametrail_saved_desktop_tests PRIVATE /W4 /permissive- /utf-8)
            endif()
            add_custom_command(TARGET frametrail_saved_desktop_tests POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>"
                    "$<TARGET_FILE_DIR:frametrail_saved_desktop_tests>" VERBATIM)
            add_test(NAME desktop_analysis_intake COMMAND frametrail_saved_desktop_tests "${_fixtures}" "${_fixtures}/review.mkv" "${_detector_model}" --intake-only)
            set_tests_properties(desktop_analysis_intake PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 90 ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
            if(FRAMETRAIL_TEST_GPU)
                add_executable(frametrail_backend_desktop_tests tests/backend_desktop_tests.cpp)
                target_link_libraries(frametrail_backend_desktop_tests PRIVATE frametrail_preview_ui Qt6::Test)
                frametrail_qt_runtime(frametrail_backend_desktop_tests)
                add_custom_command(TARGET frametrail_backend_desktop_tests POST_BUILD
                    COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_backend_desktop_tests>" VERBATIM)
                add_test(NAME gpu_desktop_workflow COMMAND frametrail_backend_desktop_tests "${_fixtures}" "${_detection_sample}" "${_detector_model}")
                set_tests_properties(gpu_desktop_workflow PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 90 ENVIRONMENT "QT_QPA_PLATFORM=offscreen" LABELS gpu)
                if(EXISTS "${_openimages_model}")
                    add_test(NAME gpu_openimages_desktop_workflow COMMAND frametrail_backend_desktop_tests "${_fixtures}" "${_detection_sample}" "${_detector_model}" openimages)
                    set_tests_properties(gpu_openimages_desktop_workflow PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 120 ENVIRONMENT "QT_QPA_PLATFORM=offscreen" LABELS gpu)
                endif()
            endif()
            add_test(NAME desktop_saved_review COMMAND frametrail_saved_desktop_tests "${_fixtures}" "${_fixtures}/review.mkv" "${_detector_model}")
            set_tests_properties(desktop_saved_review PROPERTIES FIXTURES_REQUIRED analysis TIMEOUT 60 ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
        endif()
        add_executable(frametrail_desktop_tests tests/desktop_tests.cpp)
        target_link_libraries(frametrail_desktop_tests PRIVATE frametrail_preview_ui Qt6::Test)
        frametrail_qt_runtime(frametrail_desktop_tests)
        if(MSVC)
            target_compile_options(frametrail_desktop_tests PRIVATE /W4 /permissive- /utf-8)
        endif()
        add_custom_command(TARGET frametrail_desktop_tests POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>"
                "$<TARGET_FILE_DIR:frametrail_desktop_tests>" VERBATIM)
        add_test(NAME desktop_controls COMMAND frametrail_desktop_tests "${_fixtures}")
        if(EXISTS "${_detector_model}" AND EXISTS "${_detection_sample}")
            add_test(NAME desktop_detection COMMAND frametrail_desktop_tests "${_fixtures}" "${_detection_sample}")
            set_tests_properties(desktop_detection PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60
                ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
        endif()
        set_tests_properties(desktop_controls PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30
            ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
    endif()
endif()

# Experimental RF adapter checks are independent of its adoption decision.
if(BUILD_TESTING)
    add_executable(frametrail_rf_native_tests tests/rf_native_tests.cpp)
    target_link_libraries(frametrail_rf_native_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_rf_native_tests)
    add_test(NAME rf_adapter_contract COMMAND frametrail_rf_native_tests)
    if(FRAMETRAIL_BUILD_GUI)
        add_executable(frametrail_rf_desktop_tests tests/rf_desktop_tests.cpp)
        target_link_libraries(frametrail_rf_desktop_tests PRIVATE frametrail_preview_ui Qt6::Test)
        frametrail_qt_runtime(frametrail_rf_desktop_tests)
        add_custom_command(TARGET frametrail_rf_desktop_tests POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_rf_desktop_tests>" VERBATIM)
    endif()
    if(MSVC)
        target_compile_options(frametrail_rf_native_tests PRIVATE /W4 /permissive- /utf-8)
        if(FRAMETRAIL_BUILD_GUI)
            target_compile_options(frametrail_rf_desktop_tests PRIVATE /W4 /permissive- /utf-8)
        endif()
    endif()
endif()

if(BUILD_TESTING AND FRAMETRAIL_BUILD_GUI)
  add_executable(frametrail_guide_tests tests/guide_tests.cpp)
  target_link_libraries(frametrail_guide_tests PRIVATE frametrail_preview_ui Qt6::Test)
  target_compile_options(frametrail_guide_tests PRIVATE /utf-8)
  frametrail_qt_runtime(frametrail_guide_tests)
  add_custom_command(TARGET frametrail_guide_tests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_guide_tests>")
  add_executable(frametrail_cached_playback_tests tests/cached_playback_tests.cpp)
  target_link_libraries(frametrail_cached_playback_tests PRIVATE frametrail_preview_ui Qt6::Test)
  target_compile_options(frametrail_cached_playback_tests PRIVATE /utf-8)
  frametrail_qt_runtime(frametrail_cached_playback_tests)
  add_executable(frametrail_workflow_diagnostics tests/workflow_diagnostics.cpp)
  target_link_libraries(frametrail_workflow_diagnostics PRIVATE frametrail_preview_ui Qt6::Test)
  target_compile_options(frametrail_workflow_diagnostics PRIVATE /utf-8)
  frametrail_qt_runtime(frametrail_workflow_diagnostics)
  add_executable(frametrail_unified_workspace_tests tests/unified_workspace_tests.cpp)
  target_link_libraries(frametrail_unified_workspace_tests PRIVATE frametrail_preview_ui Qt6::Test)
  target_compile_options(frametrail_unified_workspace_tests PRIVATE /utf-8)
  frametrail_qt_runtime(frametrail_unified_workspace_tests)
  add_custom_command(TARGET frametrail_unified_workspace_tests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_unified_workspace_tests>")
  add_custom_command(TARGET frametrail_workflow_diagnostics POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_workflow_diagnostics>")
  add_custom_command(TARGET frametrail_cached_playback_tests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "$<TARGET_FILE:Qt6::Test>" "$<TARGET_FILE_DIR:frametrail_cached_playback_tests>")
endif()
