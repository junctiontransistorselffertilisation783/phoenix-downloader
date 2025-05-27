from app.repositories.download_state_store import DownloadStateStore


def test_download_state_store_upsert_and_load(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    store = DownloadStateStore()
    store.Load()
    store.Upsert_download_state(
        video_id="abc123",
        list_id="PLxyz",
        download_type="video",
        playlist_item="",
        playlist_items="",
        format_simple="720",
        format_raw="bestvideo+bestaudio/best",
        state="downloading",
        temp_dir="temp-dir",
        temp_file="temp-file.part",
        bytes_downloaded="1024",
        bytes_total="4096",
        last_progress="25",
        auto_save=True,
    )

    store.Load()
    cache_key = store.Build_cache_key("abc123", "PLxyz", "video", "", "720")
    row = store.Get_row_by_cache_key(cache_key)

    assert row.get("video_id") == "abc123"
    assert row.get("state") == "partial"
    assert row.get("bytes_downloaded") == "1024"
    assert row.get("last_progress") == "25"


def test_download_state_store_temp_progress_map(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    store = DownloadStateStore()
    store.Load()
    store.Upsert_download_state(
        video_id="a",
        list_id="",
        download_type="video",
        playlist_item="",
        playlist_items="",
        format_simple="best",
        format_raw="best",
        state="downloading",
        temp_dir="temp-a",
        last_progress="70",
        auto_save=True,
    )

    progress_map = store.Get_temp_progress_map()
    assert progress_map.get("temp-a") == 70
