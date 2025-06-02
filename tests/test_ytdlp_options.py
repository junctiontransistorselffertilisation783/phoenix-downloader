from app.core.ytdlp import build_download_options


def test_build_download_options_keeps_main_video_download_subtitle_safe():
    options = build_download_options(
        output_template="video.%(ext)s",
        quality="720p",
        download_type="video",
        progress_hook=lambda _data: None,
        download_subtitles=True,
        video_language="en",
    )

    assert options.get("format")
    assert "writesubtitles" not in options
    assert "writeautomaticsub" not in options
    assert "embedsubtitles" not in options
