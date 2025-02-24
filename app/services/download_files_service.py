import os
import shutil
import time

from app.config import (
    Get_temp_media_dir,
    TEMP_HARD_DELETE_DAYS,
    TEMP_KEEP_DAYS,
    TEMP_KEEP_FLOOR_BYTES,
    TEMP_MAX_BYTES,
)
from app.repositories.download_state_store import DownloadStateStore
from app.utils.helpers import build_copied_item, is_same_path, is_temp_cache_file


class DownloadFilesService:
    def __init__(self, cache_store=None):
        self.cache_store = cache_store

    def Handle_reuse_done_file(self, cache_rows, save_dir):
        if self.cache_store is None:
            return cache_rows, 0, [], []

        pending_rows = []
        reused_count = 0
        copied_files = []
        copied_items = []

        for cache_row in cache_rows:
            cache_key = self.cache_store.Build_cache_key(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("format_simple", ""),
            )
            if cache_key == "":
                pending_rows.append(cache_row)
                continue

            old_row = self.cache_store.Get_row_by_cache_key(cache_key)
            if str(old_row.get("state", "")).lower() != "done":
                pending_rows.append(cache_row)
                continue

            target_name = str(old_row.get("target_name", "")).strip()
            if target_name == "":
                pending_rows.append(cache_row)
                continue

            source_file = ""
            old_target_dir = str(old_row.get("target_dir", "")).strip()
            if old_target_dir != "":
                old_target_file = os.path.join(old_target_dir, target_name)
                if os.path.isfile(old_target_file):
                    source_file = old_target_file

            if source_file == "":
                old_temp_file = str(old_row.get("temp_file", "")).strip()
                if old_temp_file != "" and os.path.isfile(old_temp_file):
                    source_file = old_temp_file

            if source_file == "":
                pending_rows.append(cache_row)
                continue

            os.makedirs(save_dir, exist_ok=True)
            target_file = os.path.join(save_dir, target_name)
            target_parent = os.path.dirname(target_file)
            if target_parent != "":
                os.makedirs(target_parent, exist_ok=True)

            if not is_same_path(source_file, target_file):
                if not os.path.isfile(target_file):
                    try:
                        shutil.copy2(source_file, target_file)
                    except Exception:
                        pending_rows.append(cache_row)
                        continue

            reused_count += 1
            copied_files.append(target_name)
            copied_item = build_copied_item(target_name, save_dir, cache_row.get("video_id", ""), cache_row.get("playlist_item", ""))
            copied_items.append(copied_item)
            self.cache_store.Upsert_download_state(
                cache_row.get("video_id", ""),
                cache_row.get("list_id", ""),
                cache_row.get("download_type", ""),
                cache_row.get("playlist_item", ""),
                cache_row.get("playlist_items", ""),
                cache_row.get("format_simple", ""),
                cache_row.get("format_raw", ""),
                "done",
                temp_dir=str(old_row.get("temp_dir", "")),
                temp_file=str(old_row.get("temp_file", "")),
                target_dir=save_dir,
                target_name=target_name,
                bytes_downloaded=str(old_row.get("bytes_downloaded", "0")),
                bytes_total=str(old_row.get("bytes_total", "0")),
                last_progress="100",
                auto_save=True,
            )

        return pending_rows, reused_count, copied_files, copied_items

    def Handle_copy_final_files(self, temp_work_dir, save_dir, completed_output_files):
        copied_count = 0
        removed_temp_count = 0
        copied_relative_files = []
        for current_root, _dirs, files in os.walk(temp_work_dir):
            relative_dir = os.path.relpath(current_root, temp_work_dir)
            if relative_dir == ".":
                destination_dir = save_dir
            else:
                destination_dir = os.path.join(save_dir, relative_dir)
            os.makedirs(destination_dir, exist_ok=True)

            for file_name in files:
                if is_temp_cache_file(file_name):
                    continue

                source_file = os.path.join(current_root, file_name)
                destination_file = os.path.join(destination_dir, file_name)
                if os.path.isfile(destination_file):
                    continue
                try:
                    shutil.copy2(source_file, destination_file)
                    copied_count += 1
                    relative_file = os.path.relpath(destination_file, save_dir)
                    copied_item = build_copied_item(relative_file, save_dir)
                    for finished_item in completed_output_files:
                        finished_source = str(finished_item.get("source_file", ""))
                        if not is_same_path(finished_source, source_file):
                            continue
                        copied_item["video_id"] = str(finished_item.get("video_id", ""))
                        copied_item["playlist_item"] = str(finished_item.get("playlist_item", ""))
                        break
                    copied_relative_files.append(copied_item)
                    try:
                        os.remove(source_file)
                        removed_temp_count += 1
                    except Exception:
                        pass
                except Exception:
                    continue

        return copied_count, removed_temp_count, copied_relative_files

    def Handle_cleanup_temp_cache(self, active_temp_dir=""):
        temp_root = Get_temp_media_dir()
        if not os.path.isdir(temp_root):
            return

        now_time = time.time()
        keep_seconds = TEMP_KEEP_DAYS * 86400
        hard_seconds = TEMP_HARD_DELETE_DAYS * 86400
        max_bytes = TEMP_MAX_BYTES
        keep_floor_bytes = TEMP_KEEP_FLOOR_BYTES

        cache_store = DownloadStateStore()
        cache_store.Load()
        progress_by_temp_dir = cache_store.Get_temp_progress_map()

        folder_items = []
        total_bytes = 0
        try:
            folder_names = os.listdir(temp_root)
        except Exception:
            return

        for folder_name in folder_names:
            folder_path = os.path.join(temp_root, folder_name)
            if not os.path.isdir(folder_path):
                continue

            folder_bytes = 0
            newest_time = 0
            newest_part_time = 0
            part_bytes = 0
            try:
                for walk_root, _dirs, files in os.walk(folder_path):
                    for file_name in files:
                        file_path = os.path.join(walk_root, file_name)
                        try:
                            stat_data = os.stat(file_path)
                        except Exception:
                            continue
                        file_size = int(stat_data.st_size)
                        file_mtime = float(stat_data.st_mtime)
                        folder_bytes += file_size
                        if file_mtime > newest_time:
                            newest_time = file_mtime
                        if str(file_name).lower().endswith(".part"):
                            part_bytes += file_size
                            if file_mtime > newest_part_time:
                                newest_part_time = file_mtime
            except Exception:
                continue

            if newest_time == 0:
                try:
                    newest_time = os.path.getmtime(folder_path)
                except Exception:
                    newest_time = now_time

            folder_items.append(
                {
                    "path": folder_path,
                    "bytes": folder_bytes,
                    "newest": newest_time,
                    "newest_part": newest_part_time,
                    "part_bytes": part_bytes,
                    "last_progress": progress_by_temp_dir.get(folder_path, 0),
                }
            )
            total_bytes += folder_bytes

        for item in folder_items:
            folder_path = item["path"]
            if active_temp_dir != "" and is_same_path(folder_path, active_temp_dir):
                continue
            age_seconds = now_time - float(item["newest"])
            if age_seconds >= hard_seconds:
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    total_bytes -= int(item["bytes"])
                except Exception:
                    continue

        if total_bytes <= max_bytes:
            for item in folder_items:
                folder_path = item["path"]
                if active_temp_dir != "" and is_same_path(folder_path, active_temp_dir):
                    continue
                if not os.path.isdir(folder_path):
                    continue
                age_seconds = now_time - float(item["newest"])
                if age_seconds < keep_seconds:
                    continue
                if item["newest_part"] > 0 and (now_time - float(item["newest_part"])) < keep_seconds:
                    continue
                if int(item.get("last_progress", 0)) >= 50:
                    continue
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                except Exception:
                    continue
            return

        candidates = []
        for item in folder_items:
            folder_path = item["path"]
            if active_temp_dir != "" and is_same_path(folder_path, active_temp_dir):
                continue
            if not os.path.isdir(folder_path):
                continue
            age_seconds = now_time - float(item["newest"])
            progress_score = int(item.get("last_progress", 0))
            progress_group = 3
            if progress_score < 25:
                progress_group = 0
            elif progress_score < 50:
                progress_group = 1
            elif progress_score < 75:
                progress_group = 2
            candidates.append((progress_group, -age_seconds, progress_score, item))

        candidates.sort(key=lambda value: (value[0], value[1], value[2]))

        for progress_group, _age_sort, _progress_score, item in candidates:
            if total_bytes <= keep_floor_bytes:
                break
            if progress_group >= 3 and total_bytes <= max_bytes:
                continue
            folder_path = item["path"]
            try:
                shutil.rmtree(folder_path, ignore_errors=True)
                total_bytes -= int(item["bytes"])
            except Exception:
                continue
