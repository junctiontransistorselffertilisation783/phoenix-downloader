import pytest

from app.core.errors import DownloadRequestError
from app.services.downloader_service import DownloaderService


def test_build_download_request_video_mode_keeps_video_type():
    service = DownloaderService()
    values = {
        "url": "https://www.youtube.com/watch?v=abc123",
        "quality_data": "bestvideo+bestaudio/best",
        "quality_text": "Best",
        "audio_only": False,
        "current_info_type": "video",
    }

    url, download_type, _playlist_title, quality, count_for_prefix, playlist_items = service.Build_download_request(values)

    assert url == values["url"]
    assert download_type == "video"
    assert quality == "bestvideo+bestaudio/best"
    assert count_for_prefix == 0
    assert playlist_items == ""


def test_build_download_request_playlist_requires_selected_entry():
    service = DownloaderService()
    values = {
        "url": "https://www.youtube.com/playlist?list=PLxyz",
        "quality_data": "22",
        "quality_text": "720p",
        "audio_only": False,
        "current_info_type": "playlist",
        "selected_playlist_entry": None,
    }

    with pytest.raises(DownloadRequestError):
        service.Build_download_request(values)


def test_build_download_request_playlist_range_mode_builds_items():
    service = DownloaderService()
    values = {
        "url": "https://www.youtube.com/playlist?list=PLxyz",
        "quality_data": "22",
        "quality_text": "720p",
        "audio_only": False,
        "current_info_type": "playlist",
        "selected_playlist_entry": {"index": 1},
        "playlist_title": "Sample",
        "playlist_count": 10,
        "current_checked": False,
        "range_checked": True,
        "range_start": 2,
        "range_end": 4,
        "range_items": ["6", "8-9"],
        "current_range_text": "",
        "prefix_mode": 0,
    }

    _url, download_type, playlist_title, _quality, count_for_prefix, playlist_items = service.Build_download_request(values)

    assert download_type == "playlist"
    assert playlist_title == "Sample"
    assert count_for_prefix == 10
    assert playlist_items == "6,2-4,8-9"
