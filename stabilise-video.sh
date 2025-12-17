#!/bin/bash

function print_help {
    echo "Usage: $(basename "$0") VIDEO_PATH"
    echo "Stabilises a video by detecting motion and dynamically cropping slightly, saving alongside the original"
}
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_help
    exit 0
fi
if [ $# -ne 1 ]; then
    echo "ERROR: One video path must be specified"
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

echo "Detecting motion in $(basename "$1")"
ffmpeg -hide_banner -stats -loglevel error -i "$1" -vf vidstabdetect -f null -
echo "Stabilising video"
ffmpeg -hide_banner -stats -loglevel error \
    -i "$1" -movflags use_metadata_tags -map_metadata 0 \
    -vf vidstabtransform "${1%.*}_stable.mp4"
rm transforms.trf
echo "Video stabilisation complete"
