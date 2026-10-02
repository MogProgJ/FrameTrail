cmake_minimum_required(VERSION 3.25)
project(FrameTrail VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CTest)

# Dependencies are acquired explicitly, never downloaded during configuration.
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/dependencies/windows-ffmpeg.json" _manifest)
string(JSON _package GET "${_manifest}" archiveRoot)
set(FFMPEG_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.deps/${_package}" CACHE PATH "FFmpeg SDK root")
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

add_library(frametrail_core
    src/media_reader.cpp
    src/frame_export.cpp)
target_include_directories(frametrail_core PUBLIC include)
target_link_libraries(frametrail_core PRIVATE
    FFmpeg::avformat FFmpeg::avcodec FFmpeg::avutil FFmpeg::swscale)
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
            VERBATIM)
    endif()
endfunction()

add_executable(frametrail apps/cli/main.cpp)
target_link_libraries(frametrail PRIVATE frametrail_core)
if(MSVC)
    target_compile_options(frametrail PRIVATE /W4 /permissive- /utf-8)
endif()
frametrail_runtime(frametrail)

if(BUILD_TESTING)
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
    add_test(NAME media_contract COMMAND frametrail_media_tests "${_fixtures}")
    set_tests_properties(media_contract PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
    add_test(NAME cli_help COMMAND frametrail --help)
    add_test(NAME cli_exports COMMAND ${CMAKE_COMMAND}
        "-DCLI=$<TARGET_FILE:frametrail>" "-DFIXTURES=${_fixtures}"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tests/check_cli.cmake")
    set_tests_properties(cli_exports PROPERTIES FIXTURES_REQUIRED media TIMEOUT 30)
endif()
