from app.utils.helpers import (
    detect_url_type,
    get_list_id_from_url,
    get_video_id_from_url,
    is_youtube_url,
    normalize_url,
)


def test_normalize_url_adds_https_when_missing():
    assert normalize_url("youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"


def test_detect_url_type_mixed_watch_and_list_url():
    url = "https://www.youtube.com/watch?v=abc123&list=PLxyz"
    assert detect_url_type(url) == "mixed"


def test_detect_url_type_playlist_url():
    url = "https://www.youtube.com/playlist?list=PLxyz"
    assert detect_url_type(url) == "playlist"


def test_is_youtube_url_true_for_short_link():
    assert is_youtube_url("https://youtu.be/abc123") is True


def test_get_video_id_from_url_watch_query():
    assert get_video_id_from_url("https://www.youtube.com/watch?v=abc123") == "abc123"


def test_get_video_id_from_url_short_link():
    assert get_video_id_from_url("https://youtu.be/abc123") == "abc123"


def test_get_list_id_from_url_playlist_query():
    assert get_list_id_from_url("https://www.youtube.com/playlist?list=PLxyz") == "PLxyz"
