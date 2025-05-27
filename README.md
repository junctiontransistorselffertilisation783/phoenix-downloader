# Phoenix Downloader

Simple PyQt5 desktop app to download YouTube video/audio with playlist support.

## What It Can Do

- Load video info from YouTube URL
- Download single video or playlist range
- Audio-only mode
- Subtitle and chapter support
- Resume-friendly temp cache in AppData
- Reuse already downloaded files
- Save state and settings in SQLite
- Write app logs to file

## Requirements

- Python 3.10+
- Windows (tested flow uses AppData paths)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run App

```bash
python main.py
```

## Run Tests

```bash
python -m pytest tests
```

## Project Structure

- `app/ui/` - window and UI behavior
- `app/workers/` - background threads for info/download
- `app/services/` - download workflow and file logic
- `app/repositories/` - SQLite read/write stores
- `app/core/` - database, yt-dlp helpers, logging setup
- `app/models/` - dataclasses for app flow
- `app/utils/` - pure helper functions
- `tests/` - pytest test files

## Local Data Paths

The app stores data in Local AppData under `PhoenixDownloader`:

- `phoenix_downloader.db` - SQLite database
- `logs/app.log` - log file
- `temp_media/` - temp/resume folder

## Notes

- Some subtitle requests can fail due to YouTube rate limits (for example HTTP 429).
- The app keeps user-friendly error messages in UI and technical details in logs.
