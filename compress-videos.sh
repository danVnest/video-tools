#!/bin/bash

function print_help {
    echo "Usage: $(basename "$0") VIDEO_PATH_1 [VIDEO_PATH_2 ...]"
    echo "Compresses one or more videos, saving alongside the original(s)"
}
if [ $# -lt 1 ]; then
    echo "ERROR: At least 1 video path must be specified as an argument"
    echo ""
    print_help
    exit 1
fi
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_help  
    exit 0
fi
for arg; do
    if [ ! -f "$arg" ]; then
        echo "ERROR: '$arg' is not a file"
        echo ""
        print_help
        exit 1
    fi
done

total_original_size=0
total_compressed_size=0
if [ $# -gt 1 ]; then
    for video_path in "$@"; do
        size=$(stat -f%z "$video_path")
        total_original_size=$((total_original_size + size))
    done
    echo "Compressing $# videos (total size is $(echo "scale=2; $total_original_size / 1024 / 1024" | bc)MB)"
fi
video_index=1
for video_path in "$@"; do
    original_size=$(stat -f%z "$video_path")
    echo -e "\nCompressing $(basename "$video_path") ($(echo "scale=2; $original_size / 1024 / 1024" | bc)MB) - video $video_index of $#"
    ffmpeg -hide_banner -stats -loglevel error \
        -i "$video_path" \
        -vcodec libx265 -x265-params log-level=error \
        -pix_fmt yuv420p -vtag hvc1 -crf 28 \
        -movflags use_metadata_tags -map_metadata 0 \
        "${video_path%.*}_compressed.mp4"
    compressed_size=$(stat -f%z "${video_path%.*}_compressed.mp4")
    total_compressed_size=$((total_compressed_size + compressed_size))
    echo "$(basename "$video_path") compressed to $(echo "scale=2; $compressed_size / 1024 / 1024" | bc)MB ($(echo "scale=2; $compressed_size / $original_size" | bc)x the size of the original)"
    video_index=$((video_index + 1))
done
echo -e "\nCompression complete"
if [ $# -gt 1 ]; then
    echo "Total size of all compressed videos is $(echo "scale=2; $total_compressed_size / 1024 / 1024" | bc)MB ($(echo "scale=2; $total_compressed_size / $total_original_size" | bc)x the size of the originals)"
fi
