#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta

import cv2
import osxphotos
from osxphotos.cli.push_exif import set_options_from_metadata
from osxphotos.cli.verbose import verbose_print


def parse_arguments():
    parser = ArgumentParser(
        description="Compress and manage large video files in Apple Photos library."
    )
    parser.add_argument(
        "-l",
        "--list-only",
        action="store_true",
        help="List video names only without compression or deletion.",
    )
    parser.add_argument(
        "-n",
        "--num-videos",
        type=int,
        default=3,
        help="Specify number of largest videos to process (default: 3).",
    )
    parser.add_argument(
        "-c",
        "--crf",
        type=int,
        help="Set the compression CRF value (default: 28).",
    )
    parser.add_argument(
        "-r",
        "--replace-original",
        action="store_true",
        help="Delete original videos from the library and import compressed versions.",
    )
    parser.add_argument(
        "-t",
        "--compression-ratio-threshold",
        type=float,
        help="Only replace original videos if they are below the specified compression ratio (default: 0.75).",
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=str,
        help="Specify directory of original and/or compressed videos to use instead of searching for them.",
    )
    parser.add_argument(
        "-e",
        "--export-dir",
        type=str,
        help="Specify export directory (default: ./large-videos).",
    )
    return parser.parse_args()


def check_arguments(args):
    if args.compression_ratio_threshold and not args.replace_original:
        print(
            "Error: --compression-ratio-threshold/-t can't be used without --replace-original/-r"
        )
        sys.exit(1)
    if args.list_only and (
        args.crf is not None
        or args.replace_original
        or args.compression_ratio_threshold is not None
        or args.export_dir is not None
    ):
        print(
            "Error: --list-only/-l can't be used with --crf/-c, --replace-original/-r, --compression-ratio-threshold/-t, or --export-dir/-d"
        )
        sys.exit(1)
    if args.crf is None:
        args.crf = 28
    elif args.crf < 0 or args.crf > 51:
        print("Error: --crf/-c must be between 0 and 51")
        sys.exit(1)
    if args.compression_ratio_threshold is None:
        args.compression_ratio_threshold = 0.75
    elif args.compression_ratio_threshold < 0 or args.compression_ratio_threshold > 1:
        print("Error: --compression-ratio-threshold/-t must be between 0 and 1")
        sys.exit(1)
    if args.export_dir is None:
        args.export_dir = os.path.join(os.getcwd(), "large-videos")
    os.makedirs(args.export_dir, exist_ok=True)
    if args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory does not exist: '{args.input_dir}'")
            sys.exit(1)
        if not any(
            os.path.isfile(os.path.join(root, file))
            for root, _, files in os.walk(args.input_dir)
            for file in files
        ):
            print(f"Error: No files found in input directory: '{args.input_dir}'")
            sys.exit(1)
    return args


def compress_video(
    input_path: str,
    original_video: osxphotos.PhotoInfo | None,
    export_dir: str,
    crf: int,
) -> str | None:
    # Generate compressed video filenames
    compressed_video_name = (
        original_video.original_filename
        if original_video
        else os.path.basename(input_path)
    )
    if original_video and original_video.original_filename.endswith("_compressed.mp4"):
        print(
            f"Warning: skipping '{compressed_video_name}' as it has previously been compressed and imported to the Photos library"
        )
        return None
    compressed_video_path = os.path.join(
        export_dir, os.path.splitext(str(compressed_video_name))[0]
    )
    if original_video is None:
        compressed_video_path += "_unmatched"
    elif original_video.uuid not in compressed_video_name:
        compressed_video_path += f"_{original_video.uuid}"
    temporary_compressed_video_path = (
        compressed_video_path + "_compression_in_progress.mp4"
    )
    compressed_video_path += "_compressed.mp4"

    # Handle any existing compressed videos
    if os.path.isfile(compressed_video_path):
        print(
            f"Warning: not compressing '{compressed_video_name}' as it has been done previously\n(see '{compressed_video_path}')"
        )
        return compressed_video_path
    if input_path.endswith("_compressed.mp4"):
        print(
            f"Warning: not compressing '{compressed_video_name}' as it has been done previously, copying to export directory instead"
        )
        compressed_video_path = os.path.join(export_dir, compressed_video_name)
        if not os.path.exists(compressed_video_path):
            shutil.copy2(input_path, compressed_video_path)
        return compressed_video_path
    if os.path.isfile(temporary_compressed_video_path):
        print(
            f"Warning: not compressing '{compressed_video_name}' as an incomplete compressed video exists\n(see '{temporary_compressed_video_path}')"
        )
        return None
    if input_path.endswith("_compression_in_progress.mp4"):
        print(
            f"Warning: not compressing '{compressed_video_name}' as it appears to be an incomplete compression"
        )
        return None

    # Compress the video
    video_stats = cv2.VideoCapture(input_path)
    frames = int(video_stats.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video_stats.get(cv2.CAP_PROP_FPS)
    duration = round(frames / fps) if fps != 0 else 0
    compression_time = frames / 5 / 60
    print(
        f"Video has {frames:.0f} frames and a duration of 0{timedelta(seconds=duration)}"
    )
    print(
        f"Compression estimated to complete at {(datetime.now() + timedelta(minutes=compression_time)).strftime("%I:%M %p")} "
        f"(in {compression_time:.1f} minutes, assuming compression runs at 5fps)"
    )
    start_time = datetime.now()
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-stats",
                "-loglevel",
                "error",
                "-i",
                input_path,
                "-vcodec",
                "libx265",
                "-x265-params",
                "log-level=error",
                "-pix_fmt",
                "yuv420p",
                "-vtag",
                "hvc1",
                "-crf",
                str(crf),
                "-movflags",
                "use_metadata_tags",
                "-map_metadata",
                "0",
                temporary_compressed_video_path,
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        print(
            f"Error: Failed to compress '{compressed_video_name}', continuing with next video"
        )
        os.remove(temporary_compressed_video_path)
        return None
    os.rename(temporary_compressed_video_path, compressed_video_path)

    # Copy remaining EXIF data from original video to compressed video
    if original_video:
        write_results = osxphotos.ExifWriter(original_video).write_exif_data(
            compressed_video_path,
            set_options_from_metadata(
                osxphotos.exifwriter.ExifOptions(
                    favorite_rating=True,
                    use_persons_as_keywords=True,
                    exiftool_flags=["-extractEmbedded"],
                ),
                ["all"],
            ),
        )
        if write_results[0] or write_results[1]:
            print(
                f"Warning: Issue writing EXIF data to '{compressed_video_name}', check manually"
            )

    # Report compression results
    compressed_size = os.path.getsize(compressed_video_path)
    compression_ratio = compressed_size / os.path.getsize(input_path)
    print(
        f"'{compressed_video_name}' compressed to {compressed_size / (1024 * 1024):.0f}MB "
        f"({compression_ratio:.2f}x the size of the original) in {(datetime.now() - start_time).total_seconds()/60:.1f} minutes"
    )
    return compressed_video_path


def main():
    args = check_arguments(parse_arguments())
    photos_library = osxphotos.PhotosDB(verbose=verbose_print(), rich=True)

    # Get list of videos from input directory if specified else query photos library
    input_videos: list[dict] = []
    query_videos: list[osxphotos.PhotoInfo] = []
    if args.input_dir:
        for root, _, files in os.walk(args.input_dir):
            for file in files:
                if not file.lower().endswith(
                    (".mp4", ".mov", ".mkv", ".avi", ".m4v", ".wmv", ".flv", ".webm")
                ):
                    continue
                path = os.path.join(root, file)
                input_videos.append(
                    {
                        "name": file,
                        "path": path,
                        "size": os.path.getsize(path),
                        "original": photos_library.get_photo(
                            str(os.path.splitext(file)[0]).split("_")[
                                -2 if file.endswith("_compressed.mp4") else -1
                            ]
                        ),
                    }
                )
        input_videos.sort(reverse=True, key=lambda video: video["size"])
    else:
        query_videos = photos_library.query(
            osxphotos.QueryOptions(
                photos=False, not_edited=True, not_shared=True, not_shared_moment=True
            )
        )
        query_videos.sort(reverse=True, key=lambda video: video.original_filesize)

    # Filter for N largest videos
    video_count = len(input_videos) + len(query_videos)
    if video_count == 0:
        print("Error: No videos found")
        sys.exit(1)
    elif video_count < args.num_videos:
        print(
            f"\nOnly {video_count} videos were found which is less than the "
            f"specified limit of {args.num_videos}"
        )
    elif len(input_videos) > args.num_videos:
        input_videos = input_videos[: args.num_videos]
    elif len(query_videos) > args.num_videos:
        query_videos = query_videos[: args.num_videos]
    video_count = len(input_videos) + len(query_videos)

    # List video names and sizes only if specified
    print(
        f"\nDetails of the {video_count} largest videos in "
        f"{f'the {os.path.basename(args.input_dir)} directory' if args.input_dir else 'your Photos library'}:"
    )
    for video in input_videos:
        message_start = f"{video['size'] / (1024 * 1024):.0f}MB = '{video['name']}'"
        if video["original"] is None:
            print(f"{message_start} (no original found in Photos library)")
        else:
            print(
                f"{message_start} ({video['size'] / video['original'].original_filesize:.2f}x '{video['original'].path})'"
            )
    for video in query_videos:
        print(
            f"{video.original_filesize / (1024 * 1024):.0f}MB = '{video.original_filename}' @ '{video.path}'"
        )
    total_original_size = sum(
        video["original"].original_filesize if video["original"] else video["size"]
        for video in input_videos
    ) + sum(video.original_filesize for video in query_videos)
    print(
        f"\nTotal size of these videos is {total_original_size / (1024 * 1024):.0f}MB"
    )
    if args.list_only:
        return

    # Compress videos
    print(f"\nCompressing {video_count} videos")
    compressed_videos = []
    video_index = 1
    for video in input_videos:
        print(
            f"\nCompressing '{video["original"].original_filename if video["original"] else video["name"]}' "
            f"- video {video_index} of {video_count}"
        )
        compressed_video_path = compress_video(
            video["path"], video["original"], args.export_dir, args.crf
        )
        video_size = (
            video["original"].original_filesize if video["original"] else video["size"]
        )
        if compressed_video_path:
            compressed_size = os.path.getsize(compressed_video_path)
            compressed_videos.append(
                {
                    "name": os.path.basename(compressed_video_path),
                    "path": compressed_video_path,
                    "size": compressed_size,
                    "ratio": compressed_size / video_size,
                    "original": video["original"],
                }
            )
        else:
            total_original_size -= video_size
        video_index += 1
    for video in query_videos:
        print(
            f"\nCompressing '{video.original_filename}' - video {video_index} of {video_count}"
        )
        if video.path is None:
            print(
                f"Warning: '{video.original_filename}' not downloaded to library, skipping compression"
            )
            total_original_size -= video.original_filesize
            continue
        compressed_video_path = compress_video(
            video.path,
            video,
            args.export_dir,
            args.crf,
        )
        if compressed_video_path:
            compressed_size = os.path.getsize(compressed_video_path)
            compressed_videos.append(
                {
                    "name": os.path.basename(compressed_video_path),
                    "path": compressed_video_path,
                    "size": compressed_size,
                    "ratio": compressed_size / video.original_filesize,
                    "original": video,
                }
            )
        else:
            total_original_size -= video.original_filesize
        video_index += 1
    total_compressed_size = sum(video["size"] for video in compressed_videos)
    print(
        f"\nThe {len(compressed_videos)} compressed videos total {total_compressed_size / (1024 * 1024):.0f}MB "
        f"({total_compressed_size / total_original_size:.2f}x their total original size of {total_original_size / (1024 * 1024):.0f}MB)"
    )

    # Replace original videos if specified
    if args.replace_original:
        choice = input(
            f"\nPlease check the compressed videos here: {args.export_dir}\n"
            "Do you want to import these videos and replace the originals? (y/N): "
        )
        if not choice.lower().startswith("y"):
            return
        video_paths_to_delete = []
        for video in compressed_videos:
            if photos_library.query(osxphotos.QueryOptions(name=[video["name"]])):
                print(
                    f"Warning: '{video['name']}' already exists in the Photos library, skipping"
                )
                continue
            if video["original"] is None:
                print(
                    f"Warning: '{video['name']}' could not be matched to an original in the Photos library"
                )
                choice = input("Do you want to import anyway? (y/N): ")
                if not choice.lower().startswith("y"):
                    continue
            if video["ratio"] > args.compression_ratio_threshold:
                print(
                    f"Warning: '{video['name']}' has a compression ratio of "
                    f"{video['ratio']} (above the threshold of {args.compression_ratio_threshold})"
                )
                choice = input("Do you want to replace the original anyway? (y/N): ")
                if not choice.lower().startswith("y"):
                    continue
            try:
                subprocess.run(
                    ["osxphotos", "import", video["path"], "--favorite-rating", "5"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                print(
                    f"Error: Failed to import '{video['name']}' to Photos library, continuing with next video"
                )
                continue
            if video["original"]:
                # TODO: currently there is no way to delete a video, workaround is to add to an album and delete manually
                # TODO: consider adding option to export original to specified directory when replacing (when delete is an option)
                try:
                    osxphotos.PhotosAlbum("Replaced").add(video["original"])
                except ValueError:
                    print(
                        f"Error: '{video['name']}' was imported but failed to be added to the 'Replaced' album"
                    )
                else:
                    # print( f"Imported '{video["name"]}' to Photos library and deleted the original" )
                    print(
                        f"Imported '{video["name"]}' to Photos library and added the original to the 'Replaced' album"
                    )
            else:
                print(f"Imported '{video["name"]}' to Photos library")
            video_paths_to_delete.append(video["path"])
        choice = input(
            "\nDo you want to delete the compressed videos that have now been imported? (y/N): "
        )
        if choice.lower().startswith("y"):
            for video_path in video_paths_to_delete:
                os.remove(video_path)
            if not any(
                file for file in os.scandir(args.export_dir) if file.name != ".DS_Store"
            ):
                shutil.rmtree(args.export_dir, ignore_errors=True)
        print("\nProcess completed")


if __name__ == "__main__":
    main()
