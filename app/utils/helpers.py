import re
from urllib.parse import parse_qs, urlparse


def handle_num(value):
    if value is None:
        return 0

    try:
        number_value = float(value)
    except (TypeError, ValueError):
        return 0

    if number_value < 0:
        return 0

    return number_value


def format_bytes(byte_count):
    byte_count = handle_num(byte_count)
    if byte_count <= 0:
        return ""

    units = ["B", "KB", "MB", "GB"]
    value = float(byte_count)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

    return ""


def format_seconds(seconds):
    total_seconds = int(handle_num(seconds))
    if total_seconds <= 0:
        return ""

    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def safe_name(text):
    cleaned = str(text).strip()
    for char in '<>:"/\\|?*':
        cleaned = cleaned.replace(char, "_")

    cleaned = " ".join(cleaned.split())
    if cleaned == "":
        return "playlist"

    return cleaned


def format_duration_unknown(seconds):
    try:
        total = int(seconds)
    except Exception:
        total = 0

    if total <= 0:
        return "Unknown"

    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def normalize_url(url):
    url_text = str(url or "").strip()
    if url_text == "":
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url_text):
        return f"https://{url_text}"
    return url_text


def parse_youtube_url(url):
    url_text = normalize_url(url)
    empty_result = {
        "is_youtube": False,
        "has_list": False,
        "has_video": False,
        "path_type": "unknown",
        "query": {},
    }
    if url_text == "":
        return empty_result

    try:
        parsed = urlparse(url_text)
    except Exception:
        return empty_result

    host = str(parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]

    allowed_hosts = {
        "youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
    }
    is_youtube = host in allowed_hosts

    query = parse_qs(parsed.query)
    list_values = query.get("list", [])
    video_values = query.get("v", [])
    has_list = any(str(value).strip() != "" for value in list_values)
    has_video = any(str(value).strip() != "" for value in video_values)

    path_value = str(parsed.path or "").lower()
    path_type = "unknown"
    if path_value.startswith("/playlist"):
        path_type = "playlist"
    elif path_value.startswith("/watch"):
        path_type = "watch"
    elif path_value.startswith("/live/"):
        path_type = "live"
    elif host == "youtu.be" and path_value.strip("/") != "":
        path_type = "short_watch"
        has_video = True

    if path_type in {"watch", "live", "short_watch"} and not has_video:
        has_video = True

    return {
        "is_youtube": is_youtube,
        "has_list": has_list,
        "has_video": has_video,
        "path_type": path_type,
        "query": query,
        "path_value": path_value,
    }


def detect_url_type(url):
    parsed_info = parse_youtube_url(url)
    if not parsed_info["is_youtube"]:
        return "video"

    has_list = parsed_info["has_list"]
    has_video = parsed_info["has_video"]
    path_type = parsed_info["path_type"]

    if has_list and has_video:
        return "mixed"
    if path_type == "playlist" and has_list:
        return "playlist"
    if has_list and not has_video:
        return "playlist"
    return "video"


def is_youtube_url(url):
    return parse_youtube_url(url)["is_youtube"]


def get_video_id_from_url(url):
    parsed_info = parse_youtube_url(url)
    query = parsed_info.get("query", {})
    v_values = query.get("v", [])
    if len(v_values) > 0:
        video_id = str(v_values[0]).strip()
        if video_id != "":
            return video_id

    if parsed_info.get("path_type") == "short_watch":
        path_value = str(parsed_info.get("path_value", ""))
        return path_value.strip("/").strip()

    return ""


def get_list_id_from_url(url):
    parsed_info = parse_youtube_url(url)
    query = parsed_info.get("query", {})
    list_values = query.get("list", [])
    if len(list_values) > 0:
        list_id = str(list_values[0]).strip()
        if list_id != "":
            return list_id
    return ""


def get_simple_format_text(quality):
    quality_text = str(quality or "").strip()
    if quality_text == "":
        return "unknown"

    match = re.search(r"\b(\d{2,4})\b", quality_text)
    if match:
        return match.group(1)

    lower_text = quality_text.lower()
    if "audio" in lower_text:
        return "audio"
    if "best" in lower_text:
        return "best"
    return "custom"


def get_video_id_from_entry(entry):
    webpage_url = str(entry.get("webpage_url", "")).strip()
    if webpage_url != "":
        video_id = get_video_id_from_url(webpage_url)
        if video_id != "":
            return video_id
    return ""


def get_selected_playlist_indexes(playlist_items, total_count):
    if str(playlist_items).strip() == "":
        return list(range(1, max(0, int(total_count)) + 1))

    selected_numbers = set()
    text_items = [part.strip() for part in str(playlist_items).split(",") if part.strip() != ""]
    for text_item in text_items:
        if text_item.isdigit():
            selected_numbers.add(int(text_item))
            continue
        if "-" in text_item:
            left_right = text_item.split("-", 1)
            if len(left_right) != 2:
                continue
            left_text = left_right[0].strip()
            right_text = left_right[1].strip()
            if (not left_text.isdigit()) or (not right_text.isdigit()):
                continue
            left = int(left_text)
            right = int(right_text)
            if right < left:
                left, right = right, left
            for value in range(left, right + 1):
                selected_numbers.add(value)

    filtered = [value for value in sorted(selected_numbers) if 1 <= value <= int(total_count)]
    return filtered


def is_temp_cache_file(file_name):
    file_name_lower = str(file_name or "").lower()
    if file_name_lower.endswith(".part"):
        return True
    if file_name_lower.endswith(".ytdl"):
        return True
    if file_name_lower.endswith(".tmp"):
        return True
    return False


def is_same_path(path_a, path_b):
    path_a_text = str(path_a or "")
    path_b_text = str(path_b or "")
    return path_a_text != "" and path_b_text != "" and path_a_text.lower() == path_b_text.lower()


def build_copied_item(relative_file, target_dir="", video_id="", playlist_item=""):
    relative_text = str(relative_file or "").strip()
    return {
        "relative_file": relative_text,
        "target_name": relative_text,
        "target_dir": str(target_dir or ""),
        "video_id": str(video_id or "").strip(),
        "playlist_item": str(playlist_item or "").strip(),
    }


def build_playlist_prefix_template(add_prefix, prefix_mode, playlist_count, playlist_selected_count):
    if not add_prefix:
        return ""

    count_for_digits = int(playlist_count or 0)
    if int(prefix_mode or 0) == 1 and int(playlist_selected_count or 0) > 0:
        count_for_digits = int(playlist_selected_count or 0)

    if count_for_digits >= 100:
        digits = 3
    elif count_for_digits >= 10:
        digits = 2
    else:
        digits = 1

    if int(prefix_mode or 0) == 1:
        field_name = "playlist_autonumber"
    else:
        field_name = "playlist_index"

    return f"%({field_name})0{digits}d - "


def build_suffix_text(add_suffix, suffix_text):
    if not add_suffix:
        return ""

    suffix = str(suffix_text or "").strip()
    if suffix == "":
        return ""

    suffix = re.sub(r"[\/:*?\"<>|]", "-", suffix)
    suffix = re.sub(r"\s+", " ", suffix).strip()
    if suffix == "":
        return ""

    if not suffix.startswith(" "):
        suffix = f" {suffix}"

    return suffix


def is_subtitle_file(info_dict):
    ext_value = str(info_dict.get("ext", "")).lower()
    return ext_value in ["vtt", "srt", "ttml", "sbv", "json"]
