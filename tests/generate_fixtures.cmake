file(MAKE_DIRECTORY "${OUTPUT}")

function(make_fixture)
    execute_process(COMMAND "${FFMPEG}" -hide_banner -loglevel error -y ${ARGN}
        RESULT_VARIABLE result ERROR_VARIABLE error)
    if(NOT result EQUAL 0)
        message(FATAL_ERROR "Fixture generation failed: ${error}")
    endif()
endfunction()

make_fixture(-f lavfi -i "color=c=red:s=18x14" -frames:v 1 "${OUTPUT}/still.png")
make_fixture(-f lavfi -i "testsrc=size=64x48:rate=10:duration=1"
    -c:v mpeg4 -bf 2 -pix_fmt yuv420p "${OUTPUT}/delayed.mkv")
make_fixture(-f lavfi -i "testsrc=size=64x48:rate=10:duration=1"
    -vf "setpts=if(lt(N\,3)\,N\,2*N-2)/(10*TB)"
    -fps_mode vfr -c:v ffv1 "${OUTPUT}/variable.mkv")
make_fixture(-f lavfi -i "sine=frequency=440:duration=0.1" "${OUTPUT}/audio.wav")
make_fixture(-f lavfi -i "testsrc=size=64x48:rate=60:duration=2" -c:v ffv1 "${OUTPUT}/smooth.mkv")
file(WRITE "${OUTPUT}/invalid.txt" "This is not media.\n")

make_fixture(-f lavfi -i "color=c=red:s=64x48:r=10:d=1" -c:v ffv1 "${OUTPUT}/blank.mkv")
