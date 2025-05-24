from app.utils.helpers import get_selected_playlist_indexes, get_simple_format_text, get_video_id_from_entry


def test_get_selected_playlist_indexes_full_when_empty_items():
    assert get_selected_playlist_indexes("", 4) == [1, 2, 3, 4]


def test_get_selected_playlist_indexes_range_and_number_mix():
    result = get_selected_playlist_indexes("1-3,5", 6)
    assert result == [1, 2, 3, 5]


def test_get_selected_playlist_indexes_ignores_out_of_bounds():
    result = get_selected_playlist_indexes("0,1,8,2", 3)
    assert result == [1, 2]


def test_get_video_id_from_entry_reads_webpage_url():
    entry = {"webpage_url": "https://www.youtube.com/watch?v=abc123"}
    assert get_video_id_from_entry(entry) == "abc123"


def test_get_simple_format_text_for_audio_and_custom():
    assert get_simple_format_text("Audio only (139)") == "audio"
    assert get_simple_format_text("weird quality text") == "custom"
