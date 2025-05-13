import re

from app.core.errors import DownloadRequestError
from app.core.ytdlp import build_quality_format
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

    def Build_playlist_quality_from_selection(self, selected_text, data_value):
        selected_text = str(selected_text or "").strip().lower()
        match = re.search(r"(\d{3,4})p", selected_text)
        if match:
            height_value = int(match.group(1))
            return build_quality_format(f"{height_value}p")

        match = re.search(r"(\d{3,4})x(\d{3,4})", selected_text)
        if match:
            height_value = int(match.group(2))
            if height_value <= 240:
                return build_quality_format("240p")
            if height_value <= 480:
                return build_quality_format("480p")
            if height_value <= 720:
                return build_quality_format("720p")
            return build_quality_format("Best")

        if isinstance(data_value, str) and data_value.strip() != "":
            return data_value

        return build_quality_format("720p")

    def Build_playlist_items_range(
        self,
        total_count,
        current_checked,
        selected_entry,
        range_checked,
        start_value,
        end_value,
        range_items,
        current_range_text,
    ):
        total_count = max(0, int(total_count or 0))
        if total_count <= 0:
            return "", 0

        if current_checked and selected_entry is not None:
            index_value = int(selected_entry.get("index", 0))
            if 1 <= index_value <= total_count:
                return str(index_value), 1

        if not range_checked:
            return "", total_count

        start = int(start_value)
        end = int(end_value)
        if end < start:
            start, end = end, start

        start = max(1, min(total_count, int(start)))
        end = max(1, min(total_count, int(end)))

        items_ranges = [f"{start}-{end}"]
        items_nums = []
        all_range_items = list(range_items or []) + [str(current_range_text or "")]

        for item_text in all_range_items:
            item = str(item_text or "").strip().replace(" ", "")
            if item == "":
                continue
            if item.isdigit():
                value = int(item)
                if 1 <= value <= total_count:
                    items_nums.append(str(value))
            elif "-" in item:
                parts = item.split("-")
                if (len(parts) == 2) and (parts[0].isdigit()) and (parts[1].isdigit()):
                    left = int(parts[0])
                    right = int(parts[1])
                    if right < left:
                        left, right = right, left
                    left = max(1, min(total_count, left))
                    right = max(1, min(total_count, right))
                    if right >= left:
                        items_ranges.append(f"{left}-{right}")

        all_items = items_nums + items_ranges
        unique_items = []
        seen_items = set()
        selected_numbers = set()
        for item in all_items:
            if item not in seen_items:
                unique_items.append(item)
                seen_items.add(item)
            if "-" in item:
                left, right = item.split("-", 1)
                for number_value in range(int(left), int(right) + 1):
                    selected_numbers.add(number_value)
            elif item.isdigit():
                selected_numbers.add(int(item))

        if len(unique_items) == 0:
            return "", total_count

        return ",".join(unique_items), len(selected_numbers)

    def Build_download_request(self, values):
        url = str(values.get("url", ""))
        download_type = "video"
        playlist_title = ""
        playlist_count_for_prefix = 0
        playlist_items = ""
        quality = values.get("quality_data", "")
        if quality is None or quality == "":
            quality = str(values.get("quality_text", "")).strip()

        if values.get("audio_only", False):
            quality = "Audio only (139)"

        if values.get("current_info_type", "video") == "playlist":
            selected_entry = values.get("selected_playlist_entry")
            if selected_entry is None:
                raise DownloadRequestError("Select playlist video index first")
            download_type = "playlist"
            playlist_title = str(values.get("playlist_title", ""))
            total_playlist_count = max(0, int(values.get("playlist_count", 0) or 0))
            playlist_items, selected_count = self.Build_playlist_items_range(
                total_playlist_count,
                values.get("current_checked", False),
                selected_entry,
                values.get("range_checked", False),
                values.get("range_start", 1),
                values.get("range_end", 1),
                values.get("range_items", []),
                values.get("current_range_text", ""),
            )
            playlist_count_for_prefix = total_playlist_count
            if int(values.get("prefix_mode", 0) or 0) == 1 and selected_count > 0:
                playlist_count_for_prefix = selected_count
            if not values.get("audio_only", False):
                quality = self.Build_playlist_quality_from_selection(
                    values.get("quality_text", ""),
                    values.get("quality_data", ""),
                )

        return url, download_type, playlist_title, quality, playlist_count_for_prefix, playlist_items

    def Handle_mark_rows_state(self, cache_rows, state_text, save_dir="", last_error=""):
        for cache_row in cache_rows:
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                state_text,
                temp_dir="",
                temp_file="",
                target_dir=cache_row.get("target_dir", save_dir),
                target_name=cache_row.get("target_name", ""),
                last_error=last_error,
                auto_save=True,
            )

    def Handle_progress_update(self, cache_rows, data):
        video_id = str(data.get("video_id", "")).strip()
        playlist_item = str(data.get("playlist_item", "")).strip()
        state_text = str(data.get("state", "downloading")).strip() or "downloading"
        temp_dir = str(data.get("temp_dir", "")).strip()
        temp_file = str(data.get("temp_file", "")).strip()
        bytes_downloaded = str(data.get("bytes_downloaded", "0")).strip() or "0"
        bytes_total = str(data.get("bytes_total", "0")).strip() or "0"
        last_progress = str(data.get("last_progress", "0")).strip() or "0"

        for cache_row in cache_rows:
            row_video_id = str(cache_row.get("video_id", "")).strip()
            row_playlist_item = str(cache_row.get("playlist_item", "")).strip()
            if video_id != "" and row_video_id != video_id:
                continue
            if playlist_item != "" and row_playlist_item != playlist_item:
                continue

            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                state_text,
                temp_dir=temp_dir,
                temp_file=temp_file,
                target_dir=cache_row.get("target_dir", ""),
                target_name=cache_row.get("target_name", ""),
                bytes_downloaded=bytes_downloaded,
                bytes_total=bytes_total,
                last_progress=last_progress,
                auto_save=True,
            )

    def Handle_finish_update(self, cache_rows, copied_items, copied_files, save_dir):
        for cache_row in cache_rows:
            target_name_text = ""
            row_video_id = str(cache_row.get("video_id", "")).strip()
            row_playlist_item = str(cache_row.get("playlist_item", "")).strip()
            for copied_item in copied_items:
                copied_video_id = str(copied_item.get("video_id", "")).strip()
                copied_playlist_item = str(copied_item.get("playlist_item", "")).strip()
                if row_video_id != "" and copied_video_id != "" and row_video_id != copied_video_id:
                    continue
                if row_playlist_item != "" and copied_playlist_item != "" and row_playlist_item != copied_playlist_item:
                    continue
                target_name_text = str(copied_item.get("target_name", "")).strip()
                if target_name_text != "":
                    break

            if target_name_text == "" and len(copied_files) == 1:
                target_name_text = str(copied_files[0]).strip()

            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "done",
                temp_dir="",
                temp_file="",
                target_dir=save_dir,
                target_name=target_name_text,
                auto_save=True,
            )
