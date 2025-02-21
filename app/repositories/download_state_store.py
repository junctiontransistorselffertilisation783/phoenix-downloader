import csv
import hashlib
import os
from datetime import datetime

from app.config import Get_cache_file_path
from app.core.database import Get_db_connection, Init_db_tables
from app.models.download_record import DownloadRecord


class DownloadStateStore:
    def __init__(self):
        self.rows_by_key = {}
        self.cache_file_path = Get_cache_file_path()
        Init_db_tables()

    def Handle_now_text(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def Handle_int_value(self, value, default_value=0):
        try:
            value_text = str(value or "").strip()
            if value_text == "":
                return int(default_value)
            return int(float(value_text))
        except Exception:
            return int(default_value)

    def Build_cache_key(self, video_id, list_id, download_type, playlist_item, format_simple):
        video_text = str(video_id or "").strip()
        list_text = str(list_id or "").strip()
        type_text = str(download_type or "").strip()
        item_text = str(playlist_item or "").strip()
        format_text = str(format_simple or "").strip()
        key_text = f"{video_text}|{list_text}|{type_text}|{item_text}|{format_text}"
        key_hash = hashlib.sha1(key_text.encode("utf-8")).hexdigest()
        return key_hash[:16]

    def Build_record_from_row(self, row):
        row_data = dict(row or {})
        return DownloadRecord(
            video_id=str(row_data.get("video_id", "")),
            list_id=str(row_data.get("list_id", "")),
            download_type=str(row_data.get("download_type", "")),
            playlist_item=str(row_data.get("playlist_item", "")),
            playlist_items=str(row_data.get("playlist_items", "")),
            format_simple=str(row_data.get("format_simple", "")),
            format_raw=str(row_data.get("format_raw", "")),
            state=str(row_data.get("state", "")),
            temp_dir=str(row_data.get("temp_dir", "")),
            temp_file=str(row_data.get("temp_file", "")),
            target_dir=str(row_data.get("target_dir", "")),
            target_name=str(row_data.get("target_name", "")),
            bytes_downloaded=str(row_data.get("bytes_downloaded", "0")),
            bytes_total=str(row_data.get("bytes_total", "0")),
            last_progress=str(row_data.get("last_progress", "0")),
            last_error=str(row_data.get("last_error", "")),
            created_at=str(row_data.get("created_at", "")),
            state_changed_at=str(row_data.get("state_changed_at", "")),
            updated_at=str(row_data.get("updated_at", "")),
        )

    def Build_row_from_record(self, cache_key, record):
        return {
            "cache_key": str(cache_key or ""),
            "video_id": str(record.video_id or ""),
            "list_id": str(record.list_id or ""),
            "download_type": str(record.download_type or ""),
            "playlist_item": str(record.playlist_item or ""),
            "playlist_items": str(record.playlist_items or ""),
            "format_simple": str(record.format_simple or ""),
            "format_raw": str(record.format_raw or ""),
            "state": str(record.state or ""),
            "temp_dir": str(record.temp_dir or ""),
            "temp_file": str(record.temp_file or ""),
            "target_dir": str(record.target_dir or ""),
            "target_name": str(record.target_name or ""),
            "bytes_downloaded": str(record.bytes_downloaded or "0"),
            "bytes_total": str(record.bytes_total or "0"),
            "last_progress": str(record.last_progress or "0"),
            "last_error": str(record.last_error or ""),
            "created_at": str(record.created_at or ""),
            "state_changed_at": str(record.state_changed_at or ""),
            "updated_at": str(record.updated_at or ""),
        }

    def Normalize_loaded_row(self, row):
        fixed_row = dict(row or {})
        cache_key = str(fixed_row.get("cache_key", "")).strip()
        record = self.Build_record_from_row(fixed_row)
        if record.state_changed_at == "":
            record.state_changed_at = str(fixed_row.get("updated_at", ""))
        if record.created_at == "":
            record.created_at = str(fixed_row.get("updated_at", ""))
        return self.Build_row_from_record(cache_key, record)

    def _Insert_or_replace_row(self, row):
        with Get_db_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO download_state (
                    cache_key, video_id, list_id, download_type, playlist_item, playlist_items,
                    format_simple, format_raw, state, temp_dir, temp_file, target_dir, target_name,
                    bytes_downloaded, bytes_total, last_progress, last_error, created_at,
                    state_changed_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row.get("cache_key", "")),
                    str(row.get("video_id", "")),
                    str(row.get("list_id", "")),
                    str(row.get("download_type", "")),
                    str(row.get("playlist_item", "")),
                    str(row.get("playlist_items", "")),
                    str(row.get("format_simple", "")),
                    str(row.get("format_raw", "")),
                    str(row.get("state", "")),
                    str(row.get("temp_dir", "")),
                    str(row.get("temp_file", "")),
                    str(row.get("target_dir", "")),
                    str(row.get("target_name", "")),
                    self.Handle_int_value(row.get("bytes_downloaded", "0"), 0),
                    self.Handle_int_value(row.get("bytes_total", "0"), 0),
                    self.Handle_int_value(row.get("last_progress", "0"), 0),
                    str(row.get("last_error", "")),
                    str(row.get("created_at", "")),
                    str(row.get("state_changed_at", "")),
                    str(row.get("updated_at", "")),
                ),
            )
            connection.commit()

    def Move_old_csv_cache_on_first_load(self):
        if not os.path.isfile(self.cache_file_path):
            return

        with Get_db_connection() as connection:
            cursor = connection.execute("SELECT COUNT(1) FROM download_state")
            count_value = int(cursor.fetchone()[0] or 0)
        if count_value > 0:
            return

        try:
            with open(self.cache_file_path, "r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    cache_key = str(row.get("cache_key", "")).strip()
                    if cache_key == "":
                        continue
                    fixed_row = self.Normalize_loaded_row(row)
                    self._Insert_or_replace_row(fixed_row)
        except Exception:
            return

    def Load(self):
        self.Move_old_csv_cache_on_first_load()
        self.rows_by_key = {}
        with Get_db_connection() as connection:
            cursor = connection.execute("SELECT * FROM download_state")
            for row in cursor.fetchall():
                row_dict = dict(row)
                cache_key = str(row_dict.get("cache_key", "")).strip()
                if cache_key == "":
                    continue
                self.rows_by_key[cache_key] = self.Normalize_loaded_row(row_dict)
        self.Recover_interrupted_rows()

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
                self._Insert_or_replace_row(row)

    def Save(self):
        return

    def Get_row_by_cache_key(self, cache_key):
        key_text = str(cache_key or "").strip()
        if key_text == "":
            return {}
        return dict(self.rows_by_key.get(key_text, {}))

    def Get_temp_progress_map(self):
        progress_by_temp_dir = {}
        with Get_db_connection() as connection:
            cursor = connection.execute(
                """
                SELECT temp_dir, MAX(last_progress) as max_progress
                FROM download_state
                WHERE temp_dir != ''
                GROUP BY temp_dir
                """
            )
            for row in cursor.fetchall():
                temp_dir_text = str(row["temp_dir"] or "").strip()
                if temp_dir_text == "":
                    continue
                progress_by_temp_dir[temp_dir_text] = self.Handle_int_value(row["max_progress"], 0)
        return progress_by_temp_dir

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

        old_row = self.rows_by_key.get(cache_key, {})
        record = self.Build_record_from_row(old_row)
        record.video_id = str(video_id or "")
        record.list_id = str(list_id or "")
        record.download_type = str(download_type or "")
        record.playlist_item = str(playlist_item or "")
        record.playlist_items = str(playlist_items or "")
        record.format_simple = str(format_simple or "")
        record.format_raw = str(format_raw or "")
        new_state = str(state or "")
        old_state = str(record.state or "")
        record.state = new_state

        if new_state != old_state:
            record.state_changed_at = self.Handle_now_text()
        elif str(record.state_changed_at).strip() == "":
            record.state_changed_at = self.Handle_now_text()

        if temp_dir != "":
            record.temp_dir = str(temp_dir)
        if temp_file != "":
            record.temp_file = str(temp_file)
        if target_dir != "":
            record.target_dir = str(target_dir)
        if target_name != "":
            record.target_name = str(target_name)
        if str(record.created_at).strip() == "":
            record.created_at = self.Handle_now_text()
        if bytes_downloaded != "":
            record.bytes_downloaded = str(bytes_downloaded)
        if bytes_total != "":
            record.bytes_total = str(bytes_total)
        if last_progress != "":
            record.last_progress = str(last_progress)
        if last_error != "":
            record.last_error = str(last_error)

        record.updated_at = self.Handle_now_text()
        row = self.Build_row_from_record(cache_key, record)
        self.rows_by_key[cache_key] = row
        self._Insert_or_replace_row(row)
