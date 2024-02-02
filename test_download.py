"""
YouTube video downloader - test Script
Created: Feb 2, 2024
creator: Mahmoud Emad
"""
from pathlib import Path

import yt_dlp


# Simple quality dictionary to use easy names from user
quality_dict = {
    "low": "(bv[height<=240][ext=mp4][container=mp4_dash] +139)/bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240][ext=mp4]/best",
    "medium": "(wv[height>=480][ext=mp4][container=mp4_dash] +139)/bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
    "high": "(wv[height>=720][ext=mp4][container=mp4_dash] +139)/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
}


# Method to download the video from the url
def download_video(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# Method to handle the user inputs for video download
def Handle_video_downlaod():
    # take the user inputs
    url = input("Enter the URL: ").strip()
    quality = input("Enter the quality (low / medium / high): ").strip().lower()
    output_path = input("Enter the output path: ").strip()

    # validate the user inputs
    if url == "":
        print("URL is required.")
        return

    if quality not in quality_dict:
        print("Quality must be low or medium or high.")
        return

    # make output folder path
    downloads_folder = Path.cwd() / "downloads"

    if output_path == "":
        folder_path = downloads_folder
    else:
        user_path = Path(output_path).expanduser()
        if user_path.is_absolute():
            folder_path = user_path
        else:
            folder_path = downloads_folder / user_path

    folder_path.mkdir(parents=True, exist_ok=True)

    # create yt_dlp options
    ydl_opts = {
        "format": quality_dict[quality],
        "outtmpl": str(folder_path / "%(title)s.%(ext)s"),
    }

    print(f"Output path: {folder_path}")
    print("Start download...")

    # start download
    download_video(url, ydl_opts)


def main():
    Handle_video_downlaod()


if __name__ == "__main__":
    main()
