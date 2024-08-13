#!/bin/bash

if [ $# -lt 2 ]; then
  echo "ERROR: at least 2 video paths must be specified as arguments"
  exit 1
fi

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
