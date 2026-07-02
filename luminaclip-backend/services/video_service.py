"""
Video Service — İndirme, ses çıkarma, klip kesme
"""
import os
import asyncio
import yt_dlp
import ffmpeg
import aiofiles
from pathlib import Path

TEMP_DIR = "/tmp/luminaclip"
os.makedirs(TEMP_DIR, exist_ok=True)

async def download_youtube(url: str, job_id: str) -> str:
    """YouTube videosunu indirir, ses dosyası döndürür."""
    output_path = f"{TEMP_DIR}/{job_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_path}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
    }

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: _download(url, ydl_opts))

    return f"{output_path}.mp3"

def _download(url: str, opts: dict):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def extract_audio(video_path: str, job_id: str) -> str:
    """Video dosyasından ses çıkarır."""
    audio_path = f"{TEMP_DIR}/{job_id}_audio.mp3"
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, acodec="mp3", audio_bitrate="192k")
        .overwrite_output()
        .run(quiet=True)
    )
    return audio_path

async def cut_clip(
    source_path: str,
    start: float,
    end: float,
    output_path: str,
    language: str = "ar"
) -> str:
    """Video'dan klip keser, altyazı ekler."""
    duration = end - start

    # Frame-accurate kesme — senkron hatası olmaması için
    (
        ffmpeg
        .input(source_path, ss=start, t=duration)
        .output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            video_bitrate="2000k",
            audio_bitrate="192k",
            vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            r=30,
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path

async def get_video_duration(path: str) -> float:
    """Video süresini döndürür."""
    probe = ffmpeg.probe(path)
    return float(probe["format"]["duration"])

async def cleanup(job_id: str):
    """Geçici dosyaları temizler."""
    import glob
    for f in glob.glob(f"{TEMP_DIR}/{job_id}*"):
        try:
            os.remove(f)
        except:
            pass
