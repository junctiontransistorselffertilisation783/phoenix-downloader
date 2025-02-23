from app.utils.helpers import (
    get_list_id_from_url,
    get_selected_playlist_indexes,
    get_simple_format_text,
    get_video_id_from_entry,
    get_video_id_from_url,
)


class DownloaderService:
    def __init__(self, cache_store=None):
        self.cache_store = cache_store

    def Build_download_cache_rows(self, download_url, download_type, quality, playlist_items, target_dir, playlist_entries):
        rows = []
        format_raw = str(quality or "")
        format_simple = get_simple_format_text(quality)
        list_id = get_list_id_from_url(download_url)

        if download_type == "playlist":
            total_count = len(playlist_entries)
            selected_indexes = get_selected_playlist_indexes(playlist_items, total_count)
            if len(selected_indexes) == 0:
                selected_indexes = list(range(1, total_count + 1))

            for index_value in selected_indexes:
                if index_value < 1 or index_value > len(playlist_entries):
                    continue
                entry = playlist_entries[index_value - 1]
                video_id = get_video_id_from_entry(entry)
                rows.append(
                    {
                        "video_id": video_id,
                        "list_id": list_id,
                        "download_type": "playlist",
                        "playlist_item": str(index_value),
                        "playlist_items": str(playlist_items or ""),
                        "format_simple": format_simple,
                        "format_raw": format_raw,
                        "target_dir": target_dir,
                    }
                )
            return rows

        video_id = get_video_id_from_url(download_url)
        rows.append(
            {
                "video_id": video_id,
                "list_id": list_id,
                "download_type": "video",
                "playlist_item": "",
                "playlist_items": "",
                "format_simple": format_simple,
                "format_raw": format_raw,
                "target_dir": target_dir,
            }
        )
        return rows
