from app.utils.helpers import format_duration_unknown, handle_num


def build_subtitle_profile(info_dict):
    subtitles = info_dict.get("subtitles") or {}
    auto_captions = info_dict.get("automatic_captions") or {}

    manual_langs = sorted(list(subtitles.keys()))
    auto_langs = sorted(list(auto_captions.keys()))

    preferred_order = ["en", "en-orig", "ar"]
    preferred_available = []
    for lang in preferred_order:
        if (lang in manual_langs) or (lang in auto_langs):
            preferred_available.append(lang)

    return {
        "manual_langs": manual_langs,
        "auto_langs": auto_langs,
        "manual_count": len(manual_langs),
        "auto_count": len(auto_langs),
        "has_any": (len(manual_langs) > 0) or (len(auto_langs) > 0),
        "preferred_available": preferred_available,
    }


def build_subtitle_languages(video_language):
    lang = str(video_language or "").strip().lower()
    if lang.startswith("ar"):
        return ["ar.*", "en.*"]
    return ["en.*", "ar.*"]


def build_subtitle_passes(download_subtitles, video_language=""):
    if not download_subtitles:
        return []

    subtitle_langs = build_subtitle_languages(video_language)

    subtitle_base = {
        "subtitleslangs": subtitle_langs,
        "subtitlesformat": "srt/best",
        "sleep_subtitles": 2,
    }

    return [
        {
            "name": "manual subtitles",
            "options": {
                **subtitle_base,
                "writesubtitles": True,
                "writeautomaticsub": False,
            },
        },
        {
            "name": "auto subtitles",
            "options": {
                **subtitle_base,
                "writesubtitles": False,
                "writeautomaticsub": True,
            },
        },
    ]


def build_quality_format(quality):
    if ("+" in quality) or ("/" in quality) or ("[" in quality):
        return quality

    if quality == "Audio only (139)":
        return "139/ba[ext=m4a]"

    if quality == "240p":
        resolution = "240"
    elif quality == "480p":
        resolution = "480"
    elif quality == "720p":
        resolution = "720"
    else:
        resolution = ""

    if resolution != "":
        return (
            f"(bv[height<={resolution}][ext=mp4][container=mp4_dash]+139)/"
            f"(bv[height<={resolution}][ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
            f"best[height<={resolution}][ext=mp4]/best"
        )

    return "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best"


def build_download_options(output_template, quality, download_type, progress_hook, playlist_items="", download_subtitles=False, video_language=""):
    ydl_opts = {
        "format": build_quality_format(quality),
        "outtmpl": output_template,
        "noplaylist": download_type != "playlist",
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,
        "overwrites": False,
        "merge_output_format": "mp4",
    }

    if download_type == "playlist":
        ydl_opts["ignoreerrors"] = True
        playlist_items_text = str(playlist_items or "").strip()
        if playlist_items_text != "":
            ydl_opts["playlist_items"] = playlist_items_text

    return ydl_opts


def is_subtitle_error(error_text):
    error_text = str(error_text).lower()
    subtitle_words = [
        "subtitle",
        "subtitles",
        "automatic captions",
        "requested format not available",
        "unable to download video subtitles",
    ]
    return any(word in error_text for word in subtitle_words)


def build_subtitle_download_options(output_template, progress_hook, subtitle_options, download_type="video", playlist_items=""):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": download_type != "playlist",
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
        "continuedl": True,
        "overwrites": False,
    }
    if download_type == "playlist":
        playlist_items_text = str(playlist_items or "").strip()
        if playlist_items_text != "":
            ydl_opts["playlist_items"] = playlist_items_text
    ydl_opts.update(subtitle_options)
    return ydl_opts


def get_progress_stream_size(format_info, duration_seconds):
    if not isinstance(format_info, dict):
        return 0

    size_value = format_info.get("filesize")
    if size_value:
        return handle_num(size_value)

    size_value = format_info.get("filesize_approx")
    if size_value:
        return handle_num(size_value)

    tbr_value = format_info.get("tbr")
    if tbr_value and duration_seconds:
        return handle_num((float(tbr_value) * 1000 / 8) * float(duration_seconds))

    return 0


def get_progress_item_key(info_dict):
    video_id = str(info_dict.get("id", "")).strip()
    if video_id != "":
        return video_id

    title_text = str(info_dict.get("title", "")).strip()
    if title_text != "":
        return f"title::{title_text}"

    return "default-item"


def get_progress_stream_key(info_dict):
    format_id = str(info_dict.get("format_id", "")).strip()
    if format_id != "":
        return format_id

    ext_value = str(info_dict.get("ext", "")).strip()
    if ext_value != "":
        return ext_value

    return "main-stream"


def compute_combined_progress(item_state, stream_key, downloaded_now, total_bytes, total_estimate):
    runtime_stream_total = 0
    if total_bytes is not None:
        runtime_stream_total = handle_num(total_bytes)
    elif total_estimate is not None:
        runtime_stream_total = handle_num(total_estimate)

    stream_downloaded = item_state["stream_downloaded"]
    stream_downloaded[stream_key] = max(downloaded_now, stream_downloaded.get(stream_key, 0))

    stream_totals = item_state["stream_totals"]
    if runtime_stream_total > 0:
        stream_totals[stream_key] = max(runtime_stream_total, stream_totals.get(stream_key, 0))

    if runtime_stream_total > 0:
        item_state["runtime_total"] = max(item_state["runtime_total"], runtime_stream_total)

    downloaded_total = sum(handle_num(stream_value) for stream_value in stream_downloaded.values())
    streams_total_sum = sum(handle_num(total_value) for total_value in stream_totals.values())
    known_total = max(item_state["expected_total"], item_state["runtime_total"], streams_total_sum)
    if known_total > 0:
        percent_value = int((downloaded_total / known_total) * 100)
        if percent_value > 99:
            percent_value = 99
        if percent_value < item_state["last_percent"]:
            percent_value = item_state["last_percent"]
        item_state["last_percent"] = percent_value
        return percent_value, downloaded_total, known_total

    fallback_percent = item_state["last_percent"]
    if runtime_stream_total > 0 and downloaded_now > 0:
        fallback_percent = int((downloaded_now / runtime_stream_total) * 100)
        if fallback_percent > 99:
            fallback_percent = 99
        if fallback_percent < item_state["last_percent"]:
            fallback_percent = item_state["last_percent"]
        item_state["last_percent"] = fallback_percent

    return fallback_percent, downloaded_total, known_total


def get_size_bytes(format_info, duration_seconds):
    if "filesize" in format_info and format_info["filesize"]:
        return int(format_info["filesize"])

    if "filesize_approx" in format_info and format_info["filesize_approx"]:
        return int(format_info["filesize_approx"])

    if "tbr" in format_info and format_info["tbr"] and duration_seconds:
        return int((float(format_info["tbr"]) * 1000 / 8) * float(duration_seconds))

    return 0


def build_playlist_quality_items():
    return [
        {
            "label": "Best available",
            "format": "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4][container=mp4_dash]+140)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best",
        },
        {
            "label": "1080p or lower",
            "format": "(bv[height<=1080][ext=mp4][container=mp4_dash]+139)/(bv[height<=1080][ext=mp4][container=mp4_dash]+140)/(bv[height<=1080][ext=mp4]+ba[ext=m4a])/best[height<=1080][ext=mp4]/best[height<=1080]/best",
        },
        {
            "label": "720p or lower",
            "format": "(bv[height<=720][ext=mp4][container=mp4_dash]+139)/(bv[height<=720][ext=mp4][container=mp4_dash]+140)/(bv[height<=720][ext=mp4]+ba[ext=m4a])/best[height<=720][ext=mp4]/best[height<=720]/best",
        },
        {
            "label": "480p or lower",
            "format": "(bv[height<=480][ext=mp4][container=mp4_dash]+139)/(bv[height<=480][ext=mp4][container=mp4_dash]+140)/(bv[height<=480][ext=mp4]+ba[ext=m4a])/best[height<=480][ext=mp4]/best[height<=480]/best",
        },
        {
            "label": "Audio only",
            "format": "140/139/ba[ext=m4a]/ba",
        },
    ]


def build_quality_items(formats, duration_seconds):
    quality_items = []
    filtered_formats = [
        format_info
        for format_info in formats
        if (format_info.get("ext") in ["mp4", "m4a"])
        and (format_info.get("container") in ["mp4_dash", "m4a_dash"])
    ]

    if len(filtered_formats) == 0:
        filtered_formats = [
            format_info for format_info in formats if (format_info.get("ext") in ["mp4", "m4a"])
        ]

    for i, format_info in enumerate(filtered_formats):
        format_id = str(format_info.get("format_id", "N/A"))
        resolution = str(format_info.get("resolution", "N/A"))
        extension = str(format_info.get("ext", "N/A"))
        filesize = get_size_bytes(format_info, duration_seconds)

        label = f"{i+1}. {resolution:<9} - {extension:<4} - {filesize/1024/1024:.3f} MB"

        acodec = str(format_info.get("acodec", "none"))
        has_audio = acodec != "none"
        height = format_info.get("height")
        format_code = ""

        if resolution == "audio only":
            format_code = f"{format_id}/139/140/ba[ext=m4a]/ba"
        elif has_audio:
            format_code = format_id
            label = f"{label} (video+audio)"
        else:
            if height:
                format_code = (
                    f"({format_id}+139)/"
                    f"({format_id}+ba[ext=m4a])/"
                    f"({format_id}+ba)/"
                    f"(bv[height<={height}][ext=mp4][container=mp4_dash]+139)/"
                    f"(bv[height<={height}][ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
                    f"(bv[ext=mp4][container=mp4_dash]+139)/"
                    f"(bv[ext=mp4][container=mp4_dash]+ba[ext=m4a])/"
                    f"best[ext=mp4]/best"
                )

        quality_items.append({"label": label, "format": format_code})

    quality_items.append(
        {
            "label": "Best",
            "format": "(bv[ext=mp4][container=mp4_dash]+139)/(bv[ext=mp4][container=mp4_dash]+140)/(bv[ext=mp4]+ba[ext=m4a])/best[ext=mp4]/best",
        }
    )
    return quality_items


def build_video_info(info_dict, thumbnail_data):
    title = str(info_dict.get("title", "Unknown title"))
    duration_seconds = info_dict.get("duration", 0)
    duration_text = format_duration_unknown(duration_seconds)
    uploader = str(info_dict.get("uploader") or info_dict.get("channel") or "Unknown channel")
    language = str(info_dict.get("language") or "unknown")
    formats = info_dict.get("formats", [])
    quality_items = build_quality_items(formats, duration_seconds)
    subtitle_profile = build_subtitle_profile(info_dict)

    return {
        "info_type": "video",
        "title": title,
        "uploader": uploader,
        "language": language,
        "duration_text": duration_text,
        "thumbnail_data": thumbnail_data,
        "quality_items": quality_items,
        "subtitle_profile": subtitle_profile,
    }


def build_playlist_info(info_dict, thumbnail_data):
    title = str(info_dict.get("title", "Unknown playlist"))
    uploader = str(
        info_dict.get("uploader")
        or info_dict.get("channel")
        or info_dict.get("playlist_uploader")
        or "Unknown channel"
    )
    entries = info_dict.get("entries", [])
    valid_entries = []
    total_duration_seconds = 0

    for entry in entries:
        if entry:
            valid_entries.append(entry)

    playlist_count = info_dict.get("playlist_count", len(valid_entries))
    if not playlist_count:
        playlist_count = len(valid_entries)

    playlist_entries = []
    for i, entry in enumerate(valid_entries):
        duration_seconds = entry.get("duration", 0)
        if duration_seconds:
            total_duration_seconds += int(duration_seconds)

        entry_formats = entry.get("formats", [])
        entry_quality_items = []
        if entry_formats:
            entry_quality_items = build_quality_items(entry_formats, duration_seconds)

        webpage_url = entry.get("webpage_url") or entry.get("url") or ""
        playlist_entries.append(
            {
                "index": i + 1,
                "title": str(entry.get("title", f"Video {i+1}")),
                "duration_text": format_duration_unknown(duration_seconds),
                "duration_seconds": duration_seconds or 0,
                "webpage_url": str(webpage_url),
                "is_available": bool(webpage_url),
                "quality_items": entry_quality_items,
            }
        )

    return {
        "info_type": "playlist",
        "title": title,
        "uploader": uploader,
        "playlist_count": playlist_count,
        "total_duration_text": format_duration_unknown(total_duration_seconds),
        "thumbnail_data": thumbnail_data,
        "entries": playlist_entries,
        "quality_items": build_playlist_quality_items(),
    }
