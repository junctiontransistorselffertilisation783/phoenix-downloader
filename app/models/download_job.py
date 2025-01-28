from dataclasses import dataclass


@dataclass
class DownloadJob:
    url: str
    save_dir: str
    quality: str
    download_type: str = "video"
    playlist_title: str = ""
    playlist_count: int = 0
    playlist_selected_count: int = 0
    playlist_items: str = ""
    add_prefix: bool = False
    prefix_mode: int = 0
    add_suffix: bool = False
    suffix_text: str = ""
    download_subtitles: bool = False
    download_chapters: bool = False
    video_language: str = ""
