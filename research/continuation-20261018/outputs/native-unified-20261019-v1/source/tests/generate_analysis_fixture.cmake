execute_process(COMMAND "${FFMPEG}" -v error -y -f lavfi -i "color=c=black:s=1000x1000:r=10"
    -loop 1 -framerate 10 -i "${SAMPLE}"
    -filter_complex "[0:v][1:v]overlay=x=100:y=50+40*n:eval=frame" -frames:v 6 -c:v ffv1 "${OUTPUT}"
    RESULT_VARIABLE result ERROR_VARIABLE error TIMEOUT 15)
if(NOT result EQUAL 0)
    message(FATAL_ERROR "Analysis sample generation failed: ${error}")
endif()
