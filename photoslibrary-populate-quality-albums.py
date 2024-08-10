from osxphotos import PhotoInfo, PhotosDB
from osxphotos.cli.verbose import verbose_print
from osxphotos.photosalbum import PhotosAlbum


def is_bad_photo(p: PhotoInfo) -> bool:
    """Look at photo's ScoreInfo to find photos that have low scores
    (and hence might be considered bad photos)
    """
    return any(
        [
            p.score.failure < -0.1,
            p.score.harmonious_color < -0.1,
            p.score.interesting_subject < -0.7,
            p.score.intrusive_object_presence < -0.999,
            p.score.noise < -0.75,
            p.score.pleasant_composition < -0.8,
            p.score.pleasant_lighting < -0.7,
            p.score.pleasant_perspective < -0.6,
            p.score.tastefully_blurred < -0.9,
            p.score.well_framed_subject < -0.7,
            p.score.well_timed_shot < -0.7,
        ]
    )


def main():
    media = PhotosDB(verbose=verbose_print(), rich=True).photos()
    best_album = PhotosAlbum("Quality/Best", split_folder="/")
    best_media = [p for p in media if p.score.overall >= 0.9]
    best_count = len(best_album.photos())
    best_album.extend(best_media)
    best_count = len(best_album.photos()) - best_count
    print(f"Added {best_count} new items to album {best_album.name}")

    good_album = PhotosAlbum("Quality/Good", split_folder="/")
    good_media = [p for p in media if 0.75 < p.score.overall < 0.9]
    good_count = len(good_album.photos())
    good_album.extend(good_media)
    good_count = len(good_album.photos()) - good_count
    print(f"Added {good_count} new items to album {good_album.name}")

    bad_album = PhotosAlbum("Quality/Bad", split_folder="/")
    bad_media = [p for p in media if is_bad_photo(p)]
    bad_count = len(bad_album.photos())
    bad_album.extend(bad_media)
    bad_count = len(bad_album.photos()) - bad_count
    print(f"Added {bad_count} new items to album {bad_album.name}")


if __name__ == "__main__":
    main()
