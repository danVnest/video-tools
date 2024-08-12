#!/bin/bash

if [ $# -lt 1 ]; then
    echo "ERROR: At least 1 video path must be specified as an argument"
    exit 1
fi

for video_path in "$@"; do
    filesize=$(stat -f%z "$video_path")
    echo -e "\nCompressing $(basename "$video_path") ($(echo "scale=2; $filesize / 1024 / 1024" | bc)MB)"
    ffmpeg -hide_banner -stats -loglevel error \
        -i "$video_path" \
        -vcodec libx265 -x265-params log-level=error \
        -pix_fmt yuv420p -vtag hvc1 -crf 28 \
        -movflags use_metadata_tags -map_metadata 0 \
        "$video_path.compressed.mp4"
    compressed_filesize=$(stat -f%z "$video_path.compressed.mp4")
    echo "$(basename "$video_path") compressed to $(echo "scale=2; $compressed_filesize / 1024 / 1024" | bc)MB ($(echo "scale=2; $compressed_filesize / $filesize" | bc)x the size of the original)"
done

echo "Compression complete"
