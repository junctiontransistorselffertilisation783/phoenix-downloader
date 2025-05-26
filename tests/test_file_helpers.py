from app.utils.helpers import (
    build_suffix_text,
    is_same_path,
    is_subtitle_file,
    is_temp_cache_file,
)


def test_build_suffix_text_disabled_returns_empty():
    assert build_suffix_text(False, "hello") == ""


def test_build_suffix_text_replaces_invalid_chars():
    result = build_suffix_text(True, "my:/name*")
    assert result == " my--name-"


def test_is_subtitle_file_detects_known_ext():
    assert is_subtitle_file({"ext": "srt"}) is True
    assert is_subtitle_file({"ext": "mp4"}) is False


def test_is_temp_cache_file_checks_extensions():
    assert is_temp_cache_file("video.mp4.part") is True
    assert is_temp_cache_file("video.tmp") is True
    assert is_temp_cache_file("video.mp4") is False


def test_is_same_path_case_insensitive_compare():
    assert is_same_path("C:/Temp/File.mp4", "c:/temp/file.mp4") is True
    assert is_same_path("", "c:/temp/file.mp4") is False
