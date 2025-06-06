from app.core.ytdlp import build_download_options, build_shared_ydl_options, is_authentication_required_error


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
    assert options.get("sleep_requests") == 0.25
    assert options.get("extractor_args", {}).get("youtube", {}).get("player_client") == ["default", "mweb"]
    assert "writesubtitles" not in options
    assert "writeautomaticsub" not in options
    assert "embedsubtitles" not in options


def test_build_shared_ydl_options_adds_light_request_pacing():
    options = build_shared_ydl_options()

    assert options["quiet"] is True
    assert options["no_warnings"] is True
    assert options["sleep_requests"] == 0.25


def test_is_authentication_required_error_detects_bot_check_message():
    assert is_authentication_required_error("Sign in to confirm you're not a bot") is True
    assert is_authentication_required_error("Use --cookies-from-browser or --cookies for the authentication") is True
    assert is_authentication_required_error("Requested format is not available") is False
