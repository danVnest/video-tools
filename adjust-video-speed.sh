#!/bin/bash

if [ $# -ne 2 ]; then
    echo "ERROR: A video path and a speed (i.e. use '3' for a 3x speed increase) must be specified as the first and second arguments respectively"
    exit 1
fi
if ! [[ $2 =~ ^[0-9]+(\.[0-9]+)?$ ]] || (($(echo "$2 < 0.5" | bc -l) || $(echo "$2 > 100" | bc -l) || $(echo "$2 == 1" | bc -l))); then
    echo "ERROR: Speed (the second argument) must be a number between 0.5 and 100, excluding 1"
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
