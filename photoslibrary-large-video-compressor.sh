#!/bin/bash

# Default values for optional inputs
LIST_ONLY=false
NUM_VIDEOS=1
MIN_SIZE=2GB
CRF_VALUE=28
REPLACE_ORIGINAL=false
INPUT_DIR=false
EXPORT_DIR="$(pwd)/large-videos"

# Display help message
function show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -l, --list-only                List video names only without compression or deletion."
    echo "  -n, --num-videos N             Specify number of largest videos to process (default: 1)."
    echo "  -m, --min-size S               Specify the minimum video size to process (default: 2GB)."
    echo "  -c, --crf VALUE                Set the compression CRF value (default: 28)."
    echo "  -r, --replace-original         Delete original videos from the library and import compressed version."
    echo "  -i, --input-dir PATH           Specify directory of original and/or compressed videos to use instead of searching for them."
    echo "  -e, --export-dir DIR           Specify export directory (default: ./large-videos)."
    echo "  -h, --help                     Display this help message."
    exit 1
}

# Parse command-line arguments
while [[ "$1" != "" ]]; do
    case $1 in
        -l | --list-only )
            LIST_ONLY=true
            ;;
        -n | --num-videos )
            shift
            NUM_VIDEOS=$1
            ;;
        -n | --min-size )
            shift
            MIN_SIZE=$1
            ;;
        -c | --crf )
            shift
            CRF_VALUE=$1
            ;;
        -r | --replace-original )
            REPLACE_ORIGINAL=true
            ;;
        -i | --input-dir )
	        shift
	        INPUT_DIR=$1
            ;;
        -e | --export-dir )
            shift
            EXPORT_DIR=$1
            ;;
        -h | --help )
            show_help
            ;;
        * )
            echo "Invalid option: $1"
            show_help
            ;;
    esac
    shift
done

# Query for videos if input not specified
if [ "$INPUT_DIR" = false ]; then
    video_query=$(osxphotos query --only-movies --not-edited --not-favorite --min-size $MIN_SIZE)
    video_list=()
    read # Skip header line
    while IFS=',' read -r uuid filename original_filename date description title keywords albums persons path ismissing hasadjustments external_edit favorite hidden shared latitude longitude path_edited isphoto ismovie uti burst live_photo path_live_photo iscloudasset incloud date_modified portrait screenshot screen_recording slow_mo time_lapse hdr selfie panorama h_filepath_raw intrash; do
        echo $uuid
        echo $path
        echo $filename
        echo $original_filename
        size=$(stat -f "%z" "$filepath")
        video_list+=("$size $uuid $path")
    done <<< "$video_query"
    if [ ${#video_list[@]} -eq 0 ]; then
        echo "Error: No videos found that are larger than $MIN_SIZE"
        exit 1
    fi

# Get list of videos from input directory if specified
else
    if [ ! -d "$INPUT_DIR" ]; then
        echo "Error: Input directory does not exist at $INPUT_DIR"
        exit 1
    fi
    video_list=($(find "$INPUT_DIR" -type f \( -iname '*.mov' -o -iname '*.mp4' \)))
    if [ ${#video_list[@]} -eq 0 ]; then
        echo "Error: No video files found in $INPUT_DIR"
        exit 1
    fi
fi

# Filter for N largest videos
IFS=$'\n' video_list=($(sort -nr <<< "${video_list[*]}"))
unset IFS
video_list=("${video_list[@]:0:$NUM_VIDEOS}")

# List video names only if specified
if [ "$LIST_ONLY" = true ]; then
    echo "Video UUIDs and sizes:"
    for video in "${video_list[@]}"; do
        if [ "$INPUT_DIR" = false ]; then
            uuid=$(echo "$video" | awk '{print $2}')
            filepath=$(echo "$video" | cut -d' ' -f3-)
            size=$(stat -f "%z" "$filepath")
            echo "UUID: $uuid, Size: $((size / 1024 / 1024)) MB"
        else
            size=$(stat -f "%z" "$video")
            echo "File: $(basename "$video"), Size: $((size / 1024 / 1024)) MB"
        fi
    done
    exit 0
fi

# Compress videos
mkdir -p "$EXPORT_DIR"
for video in "$EXPORT_DIR"/*.*; do
    video_name=$(basename "$video")
    compressed_video="$EXPORT_DIR/${video_name%.*}_compressed.mov"
    if [ ! -f "$compressed_video" ]; then
        ffmpeg -i "$video" -vcodec libx265 -crf "$CRF_VALUE" "$compressed_video"
        exiftool -tagsFromFile "$video" -all:all -overwrite_original "$compressed_video"
done

# Replace original videos if specified
if [ "$REPLACE_ORIGINAL" = true ]; then
    for compressed_video in "$EXPORT_DIR"/*_compressed_*.mov; do
        echo "TEST"
        # osxphotos import "$compressed_video"
        # original_uuid=$(basename "$compressed_video" | sed 's/.*_\(.*\)_compressed\.mov$/\1/')
        # osxphotos delete "$original_uuid" #--yes
        # rm "$compressed_video"
    done
fi

echo "Process completed."
