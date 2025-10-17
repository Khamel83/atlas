import subprocess
from pathlib import Path


def transcribe_audio(audio_path):
    """
    Transcribes audio using whisper.cpp or another local tool.
    Assumes 'whisper' binary is installed and available in PATH.
    """
    output_txt = Path(audio_path).with_suffix(".txt")
    try:
        subprocess.run(
            [
                "whisper",
                str(audio_path),
                "--language",
                "en",
                "--model",
                "base",
                "--output_format",
                "txt",
                "--output_dir",
                str(audio_path.parent),
            ],
            check=True,
        )
    except Exception as e:
        print(f"Transcription failed for {audio_path}: {e}")
        return "Transcription error."

    if output_txt.exists():
        return output_txt.read_text()
    return "Transcription not found."
