cmake_minimum_required(VERSION 3.25)
project(FrameTrail VERSION 0.4.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)
find_package(Threads REQUIRED)
option(FRAMETRAIL_BUILD_GUI "Build the Qt desktop preview" ON)

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
foreach(_component avformat avcodec avutil swscale)
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
set(_detector_model "${CMAKE_CURRENT_SOURCE_DIR}/models/yolox_nano.onnx")
add_library(frametrail_core
    src/tracker.cpp
    src/detector.cpp
    src/media_reader.cpp
    src/frame_export.cpp
    src/preview_session.cpp)
target_include_directories(frametrail_core PUBLIC include)
target_link_libraries(frametrail_core PRIVATE
    FFmpeg::avformat FFmpeg::avcodec FFmpeg::avutil FFmpeg::swscale Threads::Threads ONNXRuntime)
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
        if(EXISTS "${_detector_model}")
            add_custom_command(TARGET ${target} POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:${target}>/models"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_detector_model}" "$<TARGET_FILE_DIR:${target}>/models/yolox_nano.onnx"
                VERBATIM)
        endif()
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
    add_library(frametrail_preview_ui apps/desktop/preview_window.cpp)
    target_include_directories(frametrail_preview_ui PUBLIC apps/desktop)
    target_link_libraries(frametrail_preview_ui PUBLIC frametrail_core Qt6::Widgets)
    if(MSVC)
        target_compile_options(frametrail_preview_ui PRIVATE /W4 /permissive- /utf-8)
    endif()
    add_executable(frametrail-desktop WIN32 apps/desktop/main.cpp)
    target_link_libraries(frametrail-desktop PRIVATE frametrail_preview_ui)
    frametrail_qt_runtime(frametrail-desktop)
endif()

if(BUILD_TESTING)
    add_executable(frametrail_tracking_tests tests/tracking_tests.cpp)
    target_link_libraries(frametrail_tracking_tests PRIVATE frametrail_core)
    if(MSVC)
        target_compile_options(frametrail_tracking_tests PRIVATE /W4 /permissive- /utf-8)
    endif()
    frametrail_runtime(frametrail_tracking_tests)
    add_test(NAME tracking_contract COMMAND frametrail_tracking_tests)
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
    if(EXISTS "${_detector_model}")
        add_test(NAME detection_inference COMMAND frametrail_detection_tests --inference "${_detector_model}" "${_fixtures}")
        set_tests_properties(detection_inference PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
        if(EXISTS "${_detection_sample}")
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
    add_test(NAME media_contract COMMAND frametrail_media_tests "${_fixtures}")
    set_tests_properties(media_contract PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_test(NAME cli_help COMMAND frametrail --help)
    add_test(NAME cli_exports COMMAND ${CMAKE_COMMAND}
        "-DCLI=$<TARGET_FILE:frametrail>" "-DFIXTURES=${_fixtures}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_cli.cmake")
    set_tests_properties(cli_exports PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_executable(frametrail_preview_tests tests/preview_tests.cpp)
    target_link_libraries(frametrail_preview_tests PRIVATE frametrail_core)
    frametrail_runtime(frametrail_preview_tests)
    add_test(NAME preview_lifecycle COMMAND frametrail_preview_tests "${_fixtures}")
    set_tests_properties(preview_lifecycle PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    if(EXISTS "${_detector_model}" AND EXISTS "${_detection_sample}")
        add_test(NAME preview_tracking COMMAND frametrail_preview_tests "${_fixtures}" "${_detector_model}" "${_detection_sample}")
        set_tests_properties(preview_tracking PROPERTIES FIXTURES_REQUIRED media TIMEOUT 60)
    endif()
    if(FRAMETRAIL_BUILD_GUI)
        find_package(Qt6 REQUIRED COMPONENTS Test)
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
