#!/bin/bash

function print_help {
    echo "Usage: $(basename "$0") VIDEO_PATH_1 VIDEO_PATH_2 [VIDEO_PATH_3 ...]"
    echo "Merges two or more videos in argument order, saving alongside the originals"
}
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_help  
    exit 0
fi
if [ $# -lt 2 ]; then
    echo "ERROR: at least 2 video paths must be specified as arguments"
    echo ""
    print_help
    exit 1
fi
for arg; do
    if [ ! -f "$arg" ]; then
        echo "ERROR: '$arg' is not a file"
        echo ""
        print_help
        exit 1
    fi
done

echo "Merging $# videos"
for video in "$@"; do
    echo file \'$video\' >>merge-videos.txt
done
# TODO: make this work for videos of different types and speeds
ffmpeg -hide_banner -stats -loglevel error \
    -f concat -safe 0 -i merge-videos.txt \
    -c copy ${1%.*}_merged.mp4 \
    -movflags use_metadata_tags -map_metadata 0
echo "Merge completed"
rm merge-videos.txt
