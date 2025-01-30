from dataclasses import dataclass


@dataclass
class DownloadRecord:
    video_id: str = ""
    list_id: str = ""
    download_type: str = ""
    playlist_item: str = ""
    playlist_items: str = ""
    format_simple: str = ""
    format_raw: str = ""
    state: str = ""
    temp_dir: str = ""
    temp_file: str = ""
    target_dir: str = ""
    target_name: str = ""
    bytes_downloaded: str = "0"
    bytes_total: str = "0"
    last_progress: str = "0"
    last_error: str = ""
    created_at: str = ""
    state_changed_at: str = ""
    updated_at: str = ""
