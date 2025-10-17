import os
import subprocess
from pathlib import Path
from typing import Optional

from .utils import log_error, log_info


def transcribe_audio(audio_path: str, log_path: str) -> Optional[str]:
    """
    Transcribes the given audio file using the local Whisper CLI tool.

    Args:
        audio_path: The absolute path to the audio file.
        log_path: The path to the log file for this ingestion run.

    Returns:
        The transcribed text as a string, or None if transcription fails.
    """
    whisper_bin = os.getenv("WHISPER_PATH", "whisper")
    output_dir = Path(audio_path).parent
    transcript_path = (
        output_dir.parent / "transcripts" / Path(audio_path).with_suffix(".txt").name
    )

    os.makedirs(transcript_path.parent, exist_ok=True)

    if transcript_path.exists():
        log_info(
            log_path,
            f"Transcript already exists for {Path(audio_path).name}, skipping transcription.",
        )
        with open(transcript_path, "r", encoding="utf-8") as f:
            return f.read()

    log_info(log_path, f"Starting transcription for {Path(audio_path).name}...")

    try:
        # Using the 'small' model for a good balance of speed and accuracy on a Mac Mini.
        command = [
            whisper_bin,
            str(audio_path),
            "--language",
            "en",
            "--model",
            "small",
            "--output_format",
            "txt",
            "--output_dir",
            str(transcript_path.parent),
        ]

        # We use Popen to better handle stdout/stderr and avoid blocking if there are issues.
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            log_error(
                log_path,
                f"Whisper CLI failed for {audio_path} with exit code {process.returncode}.",
            )
            log_error(log_path, f"Whisper STDERR: {stderr}")
            return None

        # The output file from whisper has the same name as the input file, but with .txt
        # We need to rename it to match our transcript_path convention if it's different.
        # Whisper automatically places it in the output_dir.
        original_transcript_name = Path(audio_path).with_suffix(".txt").name
        generated_path = transcript_path.parent / original_transcript_name

        if generated_path.exists() and generated_path != transcript_path:
            os.rename(generated_path, transcript_path)

        log_info(log_path, f"Successfully transcribed {Path(audio_path).name}.")

        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            log_error(
                log_path,
                f"Transcription completed, but output file not found at {transcript_path}",
            )
            return None

    except FileNotFoundError:
        log_error(
            log_path, "Transcription failed. The 'whisper' command was not found."
        )
        log_error(
            log_path,
            "Please ensure OpenAI's Whisper CLI is installed and in your system's PATH.",
        )
        log_error(
            log_path, "Installation instructions: https://github.com/openai/whisper"
        )
        return None
    except Exception as e:
        log_error(
            log_path,
            f"An unexpected error occurred during transcription for {audio_path}: {e}",
        )
        return None
