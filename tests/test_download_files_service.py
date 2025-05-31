import os
import time

from app.config import Get_temp_media_dir, TEMP_HARD_DELETE_DAYS
from app.services.download_files_service import DownloadFilesService


class FakeCacheStore:
    def __init__(self, old_row):
        self.old_row = old_row
        self.saved_rows = []

    def Build_cache_key(self, video_id, list_id, download_type, playlist_item, format_simple):
        return "cache-key"

    def Get_row_by_cache_key(self, cache_key):
        return dict(self.old_row)

    def Upsert_download_state(self, *args, **kwargs):
        self.saved_rows.append((args, kwargs))


def test_reuse_done_file_copies_existing_file(tmp_path):
    source_dir = tmp_path / "old"
    target_dir = tmp_path / "new"
    source_dir.mkdir()
    source_file = source_dir / "video.mp4"
    source_file.write_text("video", encoding="utf-8")

    cache_store = FakeCacheStore(
        {
            "state": "done",
            "target_dir": str(source_dir),
            "target_name": "video.mp4",
        }
    )
    service = DownloadFilesService(cache_store)
    cache_rows = [
        {
            "video_id": "abc",
            "list_id": "",
            "download_type": "video",
            "playlist_item": "",
            "playlist_items": "",
            "format_simple": "best",
            "format_raw": "best",
        }
    ]

    pending_rows, reused_count, copied_files, copied_items = service.Handle_reuse_done_file(cache_rows, str(target_dir))

    assert pending_rows == []
    assert reused_count == 1
    assert copied_files == ["video.mp4"]
    assert copied_items[0]["target_name"] == "video.mp4"
    assert (target_dir / "video.mp4").is_file()
    assert len(cache_store.saved_rows) == 1


def test_cleanup_temp_cache_removes_very_old_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    temp_root = Get_temp_media_dir()
    old_folder = os.path.join(temp_root, "old-job")
    os.makedirs(old_folder, exist_ok=True)
    old_file = os.path.join(old_folder, "old.part")
    with open(old_file, "w", encoding="utf-8") as file_handle:
        file_handle.write("old")

    old_time = time.time() - ((TEMP_HARD_DELETE_DAYS + 2) * 86400)
    os.utime(old_file, (old_time, old_time))
    os.utime(old_folder, (old_time, old_time))

    service = DownloadFilesService()
    service.Handle_cleanup_temp_cache()

    assert not os.path.isdir(old_folder)
