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
