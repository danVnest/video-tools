#!/bin/bash

if [ $# -ne 1 ]; then
    echo "ERROR: One video path must be specified"
    exit 1
fi

echo "Detecting motion in $(basename "$1")"
ffmpeg -hide_banner -stats -loglevel error -i "$1" -vf vidstabdetect -f null -
echo "Stabilising video"
ffmpeg -hide_banner -stats -loglevel error \
    -i "$1" -movflags use_metadata_tags -map_metadata 0 \
    -vf vidstabtransform "${1%.*}_stable.mp4"
rm transforms.trf
echo "Video stabilisation complete"
