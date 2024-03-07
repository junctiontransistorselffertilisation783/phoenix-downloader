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
                    self.rows_by_key[cache_key] = self.Normalize_loaded_row(row)
        except Exception:
            self.rows_by_key = {}

        self.Recover_interrupted_rows()

    def Normalize_loaded_row(self, row):
        fixed_row = dict(row)

        if "temp_dir" not in fixed_row:
            fixed_row["temp_dir"] = ""
        if "bytes_downloaded" not in fixed_row:
            fixed_row["bytes_downloaded"] = "0"
        if "bytes_total" not in fixed_row:
            fixed_row["bytes_total"] = "0"
        if "last_progress" not in fixed_row:
            fixed_row["last_progress"] = "0"
        if "last_error" not in fixed_row:
            fixed_row["last_error"] = ""
        if "state_changed_at" not in fixed_row:
            fixed_row["state_changed_at"] = str(fixed_row.get("updated_at", ""))
        if "created_at" not in fixed_row:
            fixed_row["created_at"] = str(fixed_row.get("updated_at", ""))

        return fixed_row

    def Recover_interrupted_rows(self):
        now_text = self.Handle_now_text()
        for cache_key in list(self.rows_by_key.keys()):
            row = self.rows_by_key.get(cache_key, {})
            state_text = str(row.get("state", "")).strip().lower()
            if state_text == "downloading":
                row["state"] = "partial"
                row["state_changed_at"] = now_text
                row["updated_at"] = now_text
                self.rows_by_key[cache_key] = row

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
            "temp_dir",
            "temp_file",
            "target_dir",
            "target_name",
            "bytes_downloaded",
            "bytes_total",
            "last_progress",
            "last_error",
            "created_at",
            "state_changed_at",
            "updated_at",
        ]

        rows = list(self.rows_by_key.values())
        temp_file_path = self.cache_file_path + ".tmp"
        try:
            with open(temp_file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    safe_row = {field: str(row.get(field, "")) for field in fieldnames}
                    writer.writerow(safe_row)
            os.replace(temp_file_path, self.cache_file_path)
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
        temp_dir="",
        temp_file="",
        target_dir="",
        target_name="",
        bytes_downloaded="",
        bytes_total="",
        last_progress="",
        last_error="",
        auto_save=False,
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
        new_state = str(state or "")
        old_state = str(row.get("state", ""))
        row["state"] = new_state

        if new_state != old_state:
            row["state_changed_at"] = self.Handle_now_text()
        elif "state_changed_at" not in row:
            row["state_changed_at"] = self.Handle_now_text()

        if temp_dir != "":
            row["temp_dir"] = str(temp_dir)
        elif "temp_dir" not in row:
            row["temp_dir"] = ""

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

        if bytes_downloaded != "":
            row["bytes_downloaded"] = str(bytes_downloaded)
        elif "bytes_downloaded" not in row:
            row["bytes_downloaded"] = "0"

        if bytes_total != "":
            row["bytes_total"] = str(bytes_total)
        elif "bytes_total" not in row:
            row["bytes_total"] = "0"

        if last_progress != "":
            row["last_progress"] = str(last_progress)
        elif "last_progress" not in row:
            row["last_progress"] = "0"

        if last_error != "":
            row["last_error"] = str(last_error)
        elif "last_error" not in row:
            row["last_error"] = ""

        row["updated_at"] = self.Handle_now_text()
        self.rows_by_key[cache_key] = row

        if auto_save:
            self.Save()
