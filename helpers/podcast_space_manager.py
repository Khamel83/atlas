# Audio Download Prevention (Added 08/22/25)
import os
import psutil
from helpers.config import load_config


def should_download_audio(podcast_title, config=None):
    """Prevent audio downloads unless explicitly allowed"""
    if not config:
        config = load_config()

    # Check if transcript-first mode is enabled
    if config.get("PODCAST_TRANSCRIPT_FIRST", "true").lower() == "true":
        priority_list = config.get("PODCAST_AUDIO_PRIORITY_LIST", "").lower().split(",")
        return any(priority.strip() in podcast_title.lower() for priority in priority_list)

    return config.get("PODCAST_DOWNLOAD_AUDIO", "false").lower() == "true"


def check_disk_space_before_download():
    """Check available disk space before any audio download"""
    disk_usage = psutil.disk_usage("/")
    available_gb = disk_usage.free / (1024**3)

    if available_gb < 10:  # Less than 10GB free
        raise Exception(f"Insufficient disk space: {available_gb:.1f}GB available")

    return available_gb