#!/bin/bash

function print_help {
    echo "Usage: $(basename "$0") VIDEO_PATH SPEED"
    echo "Adjusts the playback speed of a video, saving alongside the original"
    echo ""
    echo "Arguments:"
    echo "  VIDEO_PATH    Path to the input video file"
    echo "  SPEED         Speed multiplier (0.5-100, excluding 1)"
}
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_help
    exit 0
fi
if [ $# -ne 2 ]; then
    echo "ERROR: A video path and a speed (i.e. use '3' for a 3x speed increase) must be specified as the first and second arguments respectively"
    echo ""
    print_help
    exit 1
fi
if [ ! -f "$1" ]; then
    echo "ERROR: '$1' is not a file"
    echo ""
    print_help
    exit 1
fi
if ! [[ $2 =~ ^[0-9]+(\.[0-9]+)?$ ]] || (($(echo "$2 < 0.5" | bc -l) || $(echo "$2 > 100" | bc -l) || $(echo "$2 == 1" | bc -l))); then
    echo "ERROR: Speed (the second argument) must be a number between 0.5 and 100, excluding 1"
    echo ""
    print_help
    exit 1
fi

echo "Adjusting speed of $(basename "$1") to $2x"
filter="[0:v]setpts=(1/$2)*PTS[v]"
maps="-map [v]"
audio=$(ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$1")
if [ -n "$audio" ]; then
    filter="$filter;[0:a]atempo=$2[a]"
    maps="$maps -map [a]"
fi
ffmpeg -hide_banner -stats -loglevel error \
    -i "$1" \
    -vcodec libx265 -x265-params log-level=error -pix_fmt yuv420p -vtag hvc1 -crf 28 \
    -movflags use_metadata_tags -map_metadata 0 \
    -filter_complex "$filter" $maps \
    "${1%.*}_$2x-speed.mp4"
echo "Speed adjustment completed"
