import csv
import hashlib
import os
from datetime import datetime


class DownloadCacheStore:
    def __init__(self):
        self.rows_by_key = {}
        self.cache_file_path = self.Build_cache_file_path()

    def Build_cache_file_path(self):
        base_dir = os.getenv("LOCALAPPDATA", "")
        if base_dir == "":
            base_dir = os.path.expanduser("~")

        app_dir = os.path.join(base_dir, "PhoenixDownloader")
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "download_cache.csv")

    def Handle_now_text(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def Load(self):
        self.rows_by_key = {}
        if not os.path.isfile(self.cache_file_path):
            return

        try:
            with open(self.cache_file_path, "r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    cache_key = str(row.get("cache_key", "")).strip()
                    if cache_key == "":
                        continue
                    self.rows_by_key[cache_key] = row
        except Exception:
            self.rows_by_key = {}

    def Save(self):
        fieldnames = [
            "cache_key",
            "video_id",
            "list_id",
            "download_type",
            "playlist_item",
            "playlist_items",
            "format_simple",
            "format_raw",
            "state",
            "temp_file",
            "target_dir",
            "target_name",
            "created_at",
            "updated_at",
        ]

        rows = list(self.rows_by_key.values())
        try:
            with open(self.cache_file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    safe_row = {field: str(row.get(field, "")) for field in fieldnames}
                    writer.writerow(safe_row)
        except Exception:
            return

    def Build_cache_key(self, video_id, list_id, download_type, playlist_item, format_simple):
        video_text = str(video_id or "").strip()
        list_text = str(list_id or "").strip()
        type_text = str(download_type or "").strip()
        item_text = str(playlist_item or "").strip()
        format_text = str(format_simple or "").strip()
        key_text = f"{video_text}|{list_text}|{type_text}|{item_text}|{format_text}"
        key_hash = hashlib.sha1(key_text.encode("utf-8")).hexdigest()
        return key_hash[:16]

    def Upsert_download_state(
        self,
        video_id,
        list_id,
        download_type,
        playlist_item,
        playlist_items,
        format_simple,
        format_raw,
        state,
        temp_file="",
        target_dir="",
        target_name="",
    ):
        cache_key = self.Build_cache_key(video_id, list_id, download_type, playlist_item, format_simple)
        if cache_key == "":
            return

        row = self.rows_by_key.get(cache_key, {})
        row["cache_key"] = cache_key
        row["video_id"] = str(video_id or "")
        row["list_id"] = str(list_id or "")
        row["download_type"] = str(download_type or "")
        row["playlist_item"] = str(playlist_item or "")
        row["playlist_items"] = str(playlist_items or "")
        row["format_simple"] = str(format_simple or "")
        row["format_raw"] = str(format_raw or "")
        row["state"] = str(state or "")

        if temp_file != "":
            row["temp_file"] = str(temp_file)
        elif "temp_file" not in row:
            row["temp_file"] = ""

        if target_dir != "":
            row["target_dir"] = str(target_dir)
        elif "target_dir" not in row:
            row["target_dir"] = ""

        if target_name != "":
            row["target_name"] = str(target_name)
        elif "target_name" not in row:
            row["target_name"] = ""

        if "created_at" not in row or str(row.get("created_at", "")).strip() == "":
            row["created_at"] = self.Handle_now_text()

        row["updated_at"] = self.Handle_now_text()
        self.rows_by_key[cache_key] = row
