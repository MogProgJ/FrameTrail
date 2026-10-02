# Tests rerun without removing any user files. Use fresh names per invocation.
string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef suffix)
set(csv "${FIXTURES}/cli-${suffix}.csv")
set(preview "${FIXTURES}/cli-${suffix}.ppm")
execute_process(COMMAND "${CLI}" inspect "${FIXTURES}/delayed.mkv"
    --csv "${csv}" --preview "${preview}" --max-frames 3
    RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT result EQUAL 0 OR NOT output MATCHES "Frames decoded: 3")
    message(FATAL_ERROR "CLI decode/export failed: ${output} ${error}")
endif()
file(STRINGS "${csv}" rows)
list(LENGTH rows count)
if(NOT count EQUAL 4)
    message(FATAL_ERROR "Expected header and three CSV rows")
endif()
if(NOT EXISTS "${preview}")
    message(FATAL_ERROR "Preview export is missing")
endif()
execute_process(COMMAND "${CLI}" inspect "${FIXTURES}/still.png" --max-frames 0
    RESULT_VARIABLE result OUTPUT_QUIET ERROR_QUIET)
if(result EQUAL 0)
    message(FATAL_ERROR "CLI accepted an invalid frame limit")
endif()
execute_process(COMMAND "${CLI}" inspect "${FIXTURES}/still.png" --csv "${csv}"
    RESULT_VARIABLE result OUTPUT_QUIET ERROR_QUIET)
if(result EQUAL 0)
    message(FATAL_ERROR "CLI overwrote an existing output")
endif()
file(COPY_FILE "${FIXTURES}/still.png" "${FIXTURES}/entrée 空.png")
execute_process(COMMAND "${CLI}" inspect "${FIXTURES}/entrée 空.png"
    RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT result EQUAL 0 OR NOT output MATCHES "Frames decoded: 1")
    message(FATAL_ERROR "Unicode CLI media path failed: ${output} ${error}")
endif()
